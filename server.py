import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
import time
import uuid
import threading
import re
import hashlib
import subprocess
import concurrent.futures
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, BackgroundTasks, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import db
from ai_director import AIDirector
from audio_ingest import AudioIngestEngine
from video_pipeline import VideoPipeline, get_bin, CREATE_NO_WINDOW

app = FastAPI(title="Editize", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta pastas estáticas
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/outputs", StaticFiles(directory=os.path.join(BASE_DIR, "outputs")), name="outputs")

# Instâncias dos motores
ai_director = AIDirector()
audio_engine = AudioIngestEngine()
video_pipeline = VideoPipeline()

# Armazenamento em memória para tarefas e estado
TASKS: Dict[str, Dict[str, Any]] = {}
ACTIVE_PROJECTS: Dict[str, Dict[str, Any]] = {}
TRANSCRIPT_CACHE: Dict[str, Dict[str, Any]] = {}
MONTHLY_USAGE: Dict[str, int] = {"used": 18, "limit": 100}

# ==============================================================================
# ROTEAMENTO DE DOMÍNIO & PÁGINAS PRINCIPAIS
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_root(request: Request):
    """
    Roteador de Host:
    - Se o acesso for feito por app.editize.net (ou subdomínio app), entrega o Estúdio (Painel Logado).
    - Se for editize.net ou acesso padrão, entrega a Landing Page com recursos e planos.
    """
    host = request.headers.get("host", "").lower()
    if host.startswith("app."):
        index_path = os.path.join(BASE_DIR, "templates", "index.html")
    else:
        index_path = os.path.join(BASE_DIR, "templates", "landing.html")

    if not os.path.exists(index_path):
        index_path = os.path.join(BASE_DIR, "templates", "index.html")

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    response = HTMLResponse(content=content)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.get("/app", response_class=HTMLResponse)
async def serve_app(request: Request):
    """Painel do Estúdio Logado (app.editize.net)"""
    index_path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    response = HTMLResponse(content=content)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.get("/landing", response_class=HTMLResponse)
async def serve_landing():
    """Landing Page Oficial de editize.net"""
    index_path = os.path.join(BASE_DIR, "templates", "landing.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    response = HTMLResponse(content=content)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.get("/login", response_class=HTMLResponse)
async def serve_login():
    """Página de Login com E-mail/Senha ou Link Mágico"""
    login_path = os.path.join(BASE_DIR, "templates", "login.html")
    with open(login_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@app.get("/register", response_class=HTMLResponse)
async def serve_register():
    """Página de Cadastro e Escolha de Plano"""
    reg_path = os.path.join(BASE_DIR, "templates", "register.html")
    with open(reg_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

# ==============================================================================
# AUTENTICAÇÃO (E-MAIL, SENHA E LINK MÁGICO)
# ==============================================================================

@app.post("/api/auth/register")
async def api_register(payload: Dict[str, Any]):
    email = payload.get("email", "").strip()
    password = payload.get("password", "").strip()
    name = payload.get("name", "").strip()
    plan = payload.get("plan", "free").strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Por favor, informe um e-mail válido.")

    existing = db.get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado. Faça login.")

def set_auth_cookie(response: Response, token: str):
    response.set_cookie(key="editize_session", value=token, max_age=86400 * 30, httponly=True)
    response.set_cookie(key="cortefy_session", value=token, max_age=86400 * 30, httponly=True)

def clear_auth_cookie(response: Response):
    response.delete_cookie("editize_session")
    response.delete_cookie("cortefy_session")

def get_session_token(request: Request) -> Optional[str]:
    return request.cookies.get("editize_session") or request.cookies.get("cortefy_session")

@app.post("/api/auth/register")
async def api_register(payload: Dict[str, Any]):
    email = payload.get("email", "").strip()
    password = payload.get("password", "").strip()
    name = payload.get("name", "").strip()
    plan = payload.get("plan", "free").strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Por favor, informe um e-mail válido.")

    existing = db.get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado. Faça login.")

    user = db.create_user(email=email, password=password, name=name, plan=plan)
    token = db.create_session(user["id"])

    res = JSONResponse(content={"success": True, "user": user})
    set_auth_cookie(res, token)
    return res

@app.post("/api/auth/login")
async def api_login(payload: Dict[str, Any]):
    email = payload.get("email", "").strip()
    password = payload.get("password", "").strip()

    user = db.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado.")

    if user.get("password_hash") and db.hash_password(password) != user["password_hash"]:
        raise HTTPException(status_code=400, detail="Senha incorreta.")

    token = db.create_session(user["id"])
    res = JSONResponse(content={"success": True, "user": user})
    set_auth_cookie(res, token)
    return res

@app.post("/api/auth/magic-link")
async def api_magic_link(payload: Dict[str, Any], request: Request):
    email = payload.get("email", "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Por favor, informe um e-mail válido.")

    user = db.get_user_by_email(email)
    if not user:
        user = db.create_user(email=email, plan="free")

    token = db.create_magic_link(email)
    magic_url = f"/auth/magic?token={token}"

    return {
        "success": True,
        "message": "Link de acesso gerado com sucesso!",
        "magic_url": magic_url
    }

@app.get("/auth/magic")
async def auth_magic_verify(token: str):
    email = db.verify_magic_link(token)
    if not email:
        raise HTTPException(status_code=400, detail="Link mágico expirado ou inválido.")

    user = db.get_user_by_email(email)
    if not user:
        user = db.create_user(email=email, plan="free")

    session_token = db.create_session(user["id"])
    res = RedirectResponse(url="/app", status_code=302)
    set_auth_cookie(res, session_token)
    return res

@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    session_token = get_session_token(request)
    user = db.get_user_from_session(session_token)
    if not user:
        demo = db.get_user_by_email("demo@editize.net") or db.get_user_by_email("demo@cortefy.com.br")
        user = demo or {
            "id": "user_demo",
            "name": "Criador Editize",
            "email": "demo@editize.net",
            "plan": "creator",
            "monthly_credits": 100,
            "credits_used": MONTHLY_USAGE["used"]
        }
    return user

@app.post("/api/auth/logout")
async def api_logout(request: Request):
    token = get_session_token(request)
    if token:
        db.delete_session(token)
    res = JSONResponse(content={"success": True})
    clear_auth_cookie(res)
    return res

# ==============================================================================
# COMPRA DE PLANOS E CHECKOUT PIX
# ==============================================================================

@app.post("/api/billing/create-pix")
async def api_create_pix(payload: Dict[str, Any], request: Request):
    plan = payload.get("plan", "creator")
    amount_cents = payload.get("amount_cents", 3990)

    session_token = get_session_token(request)
    user = db.get_user_from_session(session_token) or db.get_user_by_email("demo@editize.net") or db.get_user_by_email("demo@cortefy.com.br")
    user_id = user["id"] if user else "user_demo_editize"

    payment_id = f"pay_{uuid.uuid4().hex[:8]}"

    # Gera payload Pix no formato padrão
    pix_code = f"00020126580014br.gov.bcb.pix0136editize-pay-{payment_id}5204000053039865405{amount_cents/100:.2f}5802BR5915EDITIZE SAAS6009SAO PAULO62070503***6304ABCD"
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={pix_code}"

    conn = db.get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO payments (id, user_id, plan, amount_cents, status, pix_code, qr_code_url)
    VALUES (?, ?, ?, ?, 'pending', ?, ?)
    """, (payment_id, user_id, plan, amount_cents, pix_code, qr_code_url))
    conn.commit()
    conn.close()

    return {
        "payment_id": payment_id,
        "plan": plan,
        "amount_cents": amount_cents,
        "pix_code": pix_code,
        "qr_code_url": qr_code_url
    }

@app.post("/api/billing/confirm")
async def api_confirm_pix(payload: Dict[str, Any], request: Request):
    payment_id = payload.get("payment_id")
    plan = payload.get("plan")

    conn = db.get_db()
    cursor = conn.cursor()
    if payment_id:
        cursor.execute("SELECT plan FROM payments WHERE id = ?", (payment_id,))
        row = cursor.fetchone()
        if row and not plan:
            plan = row["plan"]
        cursor.execute("UPDATE payments SET status = 'paid' WHERE id = ?", (payment_id,))
        conn.commit()
    conn.close()

    if not plan:
        plan = "creator"

    session_token = request.cookies.get("cortefy_session")
    user = db.get_user_from_session(session_token) or db.get_user_by_email("demo@cortefy.com.br")
    if user:
        db.update_user_plan(user["id"], plan)

    MONTHLY_USAGE["limit"] = 999 if plan == "pro" else 100

    return {
        "success": True,
        "message": f"Plano {plan.upper()} ativado com sucesso!",
        "plan": plan
    }

# ==============================================================================
# PIPELINE DE PROCESSAMENTO E GERAÇÃO DE CORTES COM PLAYER EMBUTIDO
# ==============================================================================

@app.get("/api/health")
async def health_check():
    ai_ready = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "online",
        "service": "Editize.net",
        "ready": ai_ready,
        "version": "3.1.0",
        "timestamp": time.time()
    }

@app.get("/api/monthly-stats")
async def get_monthly_stats(request: Request):
    session_token = get_session_token(request)
    user = db.get_user_from_session(session_token)
    if user:
        return {
            "used": user["credits_used"],
            "limit": user["monthly_credits"],
            "plan": user["plan"],
            "name": user["name"]
        }
    return MONTHLY_USAGE

@app.post("/api/monthly-stats/increment")
async def increment_monthly_stats(request: Request):
    session_token = get_session_token(request)
    user = db.get_user_from_session(session_token)
    if user:
        new_val = db.increment_user_credits_used(user["id"])
        return {"used": new_val, "limit": user["monthly_credits"]}
    MONTHLY_USAGE["used"] = min(MONTHLY_USAGE["limit"], MONTHLY_USAGE["used"] + 1)
    return MONTHLY_USAGE

@app.get("/api/video-info")
async def get_video_info(url: str):
    clean_url = (url or "").strip()
    if not clean_url:
        raise HTTPException(status_code=400, detail="URL necessária")
    info = audio_engine.get_video_metadata(clean_url)
    return info

@app.post("/api/project/analyze")
async def start_analysis(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    source_url = payload.get("source_url", "").strip()
    broll_mode = payload.get("broll_mode", "auto_extract")
    broll_url = payload.get("broll_url", "").strip()
    genre = payload.get("genre", "auto").strip()
    subtitle_style = payload.get("subtitle_style", "hormozi_pop")
    custom_color = payload.get("custom_color")
    custom_size = payload.get("custom_size")
    custom_margin = payload.get("custom_margin")
    layout = payload.get("layout", "portrait")
    speed = float(payload.get("speed", 1.0))
    enable_zoom = bool(payload.get("enable_zoom", True))
    enable_drift = bool(payload.get("enable_drift", True))

    if broll_mode == "external" and broll_url:
        layout = "split_screen"

    if not source_url:
        sample_path = os.path.join(os.path.dirname(BASE_DIR), "video_source.mp4")
        if os.path.exists(sample_path):
            source_url = sample_path
        else:
            raise HTTPException(status_code=400, detail="Por favor, forneça uma URL válida do YouTube ou arquivo.")

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    TASKS[task_id] = {
        "status": "processing",
        "progress": 5,
        "message": "Carregando o vídeo...",
        "result": None,
        "error": None
    }

    def process_task():
        heartbeat_running = True

        def heartbeat():
            messages = [
                (45, "Investigando o tema e contexto real do vídeo..."),
                (60, "Calculando o potencial de retenção e ganchos virais..."),
                (72, "Criando títulos magnéticos e legendas com SEO..."),
                (85, "Editando os vídeos dos cortes em 9:16 com legendas animadas...")
            ]
            idx = 0
            while heartbeat_running and idx < len(messages):
                time.sleep(2.0)
                if not heartbeat_running:
                    break
                prog, msg = messages[idx]
                if TASKS[task_id]["status"] == "processing":
                    TASKS[task_id]["progress"] = max(TASKS[task_id]["progress"], prog)
                    TASKS[task_id]["message"] = msg
                idx += 1

        threading.Thread(target=heartbeat, daemon=True).start()

        try:
            def update_progress(prog: int, msg: str):
                TASKS[task_id]["progress"] = prog
                TASKS[task_id]["message"] = msg

            cuts = []
            words = []
            video_title = "Vídeo Selecionado"

            # 1. Estratégia Ultra-Rápida: Cache ou Extração Direta de Legendas em 2 segundos
            cached = TRANSCRIPT_CACHE.get(source_url)
            if cached:
                update_progress(30, "Vídeo memorizado! Investigando contexto dos cortes...")
                video_title = cached.get("title", "Vídeo")
                words = cached.get("words", [])
                cuts = ai_director.analyze_virality(cached["segments"], video_title=video_title, genre=genre, batch_index=1)
            elif source_url.startswith("http://") or source_url.startswith("https://"):
                update_progress(15, "Lendo falas do vídeo em altíssima velocidade...")
                fast_sub = audio_engine.extract_youtube_transcript_fast(source_url, progress_callback=update_progress)
                if fast_sub.get("success") and fast_sub.get("segments"):
                    video_title = fast_sub.get("title", "Vídeo")
                    words = fast_sub.get("words", [])
                    TRANSCRIPT_CACHE[source_url] = {
                        "segments": fast_sub["segments"],
                        "words": words,
                        "title": video_title
                    }
                    update_progress(50, "Aprofundando na obra e momentos com maior retenção...")
                    cuts = ai_director.analyze_virality(fast_sub["segments"], video_title=video_title, genre=genre, batch_index=1)

            # 2. Fallback por Áudio leve caso não haja legendas no YouTube ou seja arquivo local
            if not cuts:
                update_progress(40, "Processando trilha de áudio...")
                if source_url.startswith("http://") or source_url.startswith("https://"):
                    audio_path, video_title = audio_engine.download_youtube_audio(source_url, progress_callback=update_progress)
                else:
                    ingest_res = audio_engine.extract_audio_from_local_file(source_url, progress_callback=update_progress)
                    audio_path = ingest_res["audio_path"]
                    video_title = ingest_res.get("title", "Vídeo")

                update_progress(60, "Identificando os melhores momentos com IA...")
                cuts = ai_director.analyze_audio_directly(audio_path, video_title=video_title, genre=genre)

                if not cuts:
                    ingest_res = audio_engine.transcribe_audio_file(audio_path, video_title=video_title, progress_callback=update_progress)
                    cuts = ai_director.analyze_virality(ingest_res["segments"], video_title=video_title, genre=genre)
                    words = ingest_res.get("words", [])

            # 3. GERA OS VÍDEOS DOS CORTES 100% EDITADOS (Player 9:16 com legendas animadas pronto)
            update_progress(65, "Renderizando os cortes virais em 9:16 com legendas animadas...")

            # 3.1 Garante que o vídeo fonte foi baixado localmente para aceleração máxima
            actual_source = source_url
            if source_url.startswith("http://") or source_url.startswith("https://"):
                url_hash = hashlib.md5(source_url.encode("utf-8")).hexdigest()[:12]
                source_cache_file = os.path.join(video_pipeline.temp_dir, f"source_{url_hash}.mp4")
                if not os.path.exists(source_cache_file) or os.path.getsize(source_cache_file) < 10000:
                    update_progress(68, "Baixando vídeo fonte em alta qualidade...")
                    ytdlp_bin = get_bin("yt-dlp")
                    ffmpeg_bin = get_bin("ffmpeg")
                    ffmpeg_dir = os.path.dirname(ffmpeg_bin) if os.path.exists(ffmpeg_bin) else ""
                    cmd_down = [
                        ytdlp_bin,
                        "--no-playlist",
                        "--force-overwrites",
                        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                        "--merge-output-format", "mp4",
                        "-o", source_cache_file
                    ]
                    if ffmpeg_dir:
                        cmd_down.extend(["--ffmpeg-location", ffmpeg_dir])
                    cmd_down.append(source_url)
                    subprocess.run(cmd_down, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=CREATE_NO_WINDOW)
                if os.path.exists(source_cache_file) and os.path.getsize(source_cache_file) > 10000:
                    actual_source = source_cache_file

            update_progress(78, "Aplicando legendas dinâmicas e enquadramento 9:16...")

            def render_one_cut(item):
                idx, c = item
                c_id = c.get("id", f"corte_{idx+1:02d}")
                out_filename = f"{c_id}_{uuid.uuid4().hex[:6]}.mp4"
                out_path = os.path.join(video_pipeline.output_dir, out_filename)
                try:
                    video_pipeline.render_viral_cut(
                        source_video=actual_source,
                        cut_info=c,
                        words=words,
                        layout=layout,
                        broll_mode=broll_mode,
                        broll_source=broll_url,
                        subtitle_style=subtitle_style,
                        custom_color=custom_color,
                        custom_font_size=custom_size,
                        custom_margin_v=custom_margin,
                        speed=speed,
                        enable_zoom=enable_zoom,
                        enable_drift=enable_drift,
                        output_file=out_path
                    )
                    c["video_url"] = f"/outputs/{out_filename}"
                    c["filename"] = out_filename
                except Exception as ex:
                    print(f"[Server] Aviso ao renderizar {c_id}: {ex}")
                    try:
                        video_pipeline.extract_or_download_segment(actual_source, c["start"], c["end"], out_path)
                        c["video_url"] = f"/outputs/{out_filename}"
                        c["filename"] = out_filename
                    except Exception:
                        pass
                return c

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                rendered_cuts = list(pool.map(render_one_cut, enumerate(cuts)))
            cuts = rendered_cuts

            heartbeat_running = False

            # Salva o projeto com todas as opções de estilo
            project_id = f"proj_{uuid.uuid4().hex[:6]}"
            ACTIVE_PROJECTS[project_id] = {
                "source_url": actual_source,
                "broll_mode": broll_mode,
                "broll_url": broll_url,
                "genre": genre,
                "subtitle_style": subtitle_style,
                "custom_color": custom_color,
                "custom_size": custom_size,
                "custom_margin": custom_margin,
                "layout": layout,
                "speed": speed,
                "enable_zoom": enable_zoom,
                "enable_drift": enable_drift,
                "title": video_title,
                "duration": 0,
                "words": words,
                "cuts": cuts
            }

            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["progress"] = 100
            TASKS[task_id]["message"] = f"Pronto! Encontramos {len(cuts)} cortes virais ranqueados com player pronto."
            TASKS[task_id]["result"] = {
                "project_id": project_id,
                "title": video_title,
                "cuts": cuts
            }
        except Exception as e:
            heartbeat_running = False
            TASKS[task_id]["status"] = "error"
            TASKS[task_id]["error"] = str(e)
            TASKS[task_id]["message"] = f"Não foi possível concluir: {str(e)[:150]}"

    threading.Thread(target=process_task, daemon=True).start()
    return {"task_id": task_id}

@app.post("/api/project/more-cuts")
async def generate_more_cuts(payload: Dict[str, Any]):
    """Gera mais 5 cortes virais com players prontos sem reprocessar o vídeo do zero."""
    project_id = payload.get("project_id")
    project = ACTIVE_PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    existing_cuts = project.get("cuts", [])
    source_url = project.get("source_url")
    genre = project.get("genre", "auto")
    video_title = project.get("title", "")

    cached = TRANSCRIPT_CACHE.get(source_url)
    segments = cached.get("segments") if cached else None

    batch_idx = (len(existing_cuts) // 5) + 1
    if segments:
        new_cuts = ai_director.analyze_virality(
            segments,
            video_title=video_title,
            genre=genre,
            batch_index=batch_idx,
            exclude_cuts=existing_cuts
        )
    else:
        new_cuts = ai_director._heuristic_fallback([{"end": 600.0}], video_title=video_title, batch_index=batch_idx)

    # Renderiza os novos cortes em 9:16 com legendas animadas em paralelo
    def render_one_new(item):
        idx, c = item
        c_id = c.get("id", f"corte_{len(existing_cuts)+idx+1:02d}")
        out_filename = f"{c_id}_{uuid.uuid4().hex[:6]}.mp4"
        out_path = os.path.join(video_pipeline.output_dir, out_filename)
        try:
            video_pipeline.render_viral_cut(
                source_video=source_url,
                cut_info=c,
                words=project.get("words", []),
                layout=project.get("layout", "portrait"),
                broll_mode=project.get("broll_mode", "auto_extract"),
                broll_source=project.get("broll_url"),
                subtitle_style=project.get("subtitle_style", "hormozi_pop"),
                custom_color=project.get("custom_color"),
                custom_font_size=project.get("custom_size"),
                custom_margin_v=project.get("custom_margin"),
                speed=project.get("speed", 1.0),
                enable_zoom=project.get("enable_zoom", True),
                enable_drift=project.get("enable_drift", True),
                output_file=out_path
            )
            c["video_url"] = f"/outputs/{out_filename}"
            c["filename"] = out_filename
        except Exception as ex:
            print(f"[Server] Aviso ao preparar novo corte {c_id}: {ex}")
            try:
                video_pipeline.extract_or_download_segment(source_url, c["start"], c["end"], out_path)
                c["video_url"] = f"/outputs/{out_filename}"
                c["filename"] = out_filename
            except Exception:
                pass
        return c

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        new_cuts = list(pool.map(render_one_new, enumerate(new_cuts)))

    project["cuts"].extend(new_cuts)
    return {
        "new_cuts": new_cuts,
        "total_cuts": len(project["cuts"])
    }

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return task

@app.post("/api/project/render")
async def start_render(payload: Dict[str, Any]):
    project_id = payload.get("project_id")
    cut_id = payload.get("cut_id")
    layout = payload.get("layout", "split_screen")
    subtitle_style = payload.get("subtitle_style", "hormozi_pop")
    custom_color = payload.get("custom_color")
    custom_font_size = payload.get("custom_font_size")
    custom_margin_v = payload.get("custom_margin_v")
    speed = float(payload.get("speed", 1.05))
    broll_mode = payload.get("broll_mode", "auto_extract")
    broll_source = payload.get("broll_source")
    enable_zoom = bool(payload.get("enable_zoom", True))
    enable_drift = bool(payload.get("enable_drift", True))

    project = ACTIVE_PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    selected_cut = next((c for c in project["cuts"] if c["id"] == cut_id), None)
    if not selected_cut:
        raise HTTPException(status_code=404, detail="Corte não encontrado.")

    MONTHLY_USAGE["used"] = min(MONTHLY_USAGE["limit"], MONTHLY_USAGE["used"] + 1)

    render_task_id = f"render_{uuid.uuid4().hex[:8]}"
    TASKS[render_task_id] = {
        "status": "processing",
        "progress": 5,
        "message": "Preparando fatiamento e legendas...",
        "output_url": None,
        "filename": None,
        "error": None
    }

    def render_worker():
        try:
            def update_cb(prog: int, msg: str):
                TASKS[render_task_id]["progress"] = prog
                TASKS[render_task_id]["message"] = msg

            out_file = video_pipeline.render_viral_cut(
                source_video=project["source_url"],
                cut_info=selected_cut,
                words=project["words"],
                layout=layout,
                broll_mode=broll_mode or project.get("broll_mode", "auto_extract"),
                broll_source=broll_source or project.get("broll_url"),
                subtitle_style=subtitle_style,
                custom_color=custom_color,
                custom_font_size=custom_font_size,
                custom_margin_v=custom_margin_v,
                speed=speed,
                enable_zoom=enable_zoom,
                enable_drift=enable_drift,
                progress_cb=update_cb
            )

            fname = os.path.basename(out_file)
            TASKS[render_task_id]["status"] = "completed"
            TASKS[render_task_id]["progress"] = 100
            TASKS[render_task_id]["message"] = "Renderização concluída com sucesso!"
            TASKS[render_task_id]["filename"] = fname
            TASKS[render_task_id]["output_url"] = f"/outputs/{fname}"
            selected_cut["video_url"] = f"/outputs/{fname}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            TASKS[render_task_id]["status"] = "error"
            TASKS[render_task_id]["error"] = str(e)
            TASKS[render_task_id]["message"] = "Não foi possível concluir a renderização do corte. Tente novamente."

    threading.Thread(target=render_worker, daemon=True).start()
    return {"render_task_id": render_task_id}

@app.get("/api/download/{filename}")
async def download_rendered_file(filename: str):
    fpath = os.path.join(BASE_DIR, "outputs", filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(fpath, media_type="video/mp4", filename=filename)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"\n⚡ [EDITIZE.NET] Servidor iniciado em http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)
