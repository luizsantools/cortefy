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
from thumbnail_generator import ThumbnailGenerator

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
thumbnail_generator = ThumbnailGenerator()

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
    custom_highlight_color = payload.get("custom_highlight_color")
    custom_font = payload.get("custom_font")
    custom_outline_color = payload.get("custom_outline_color")
    custom_outline_w = payload.get("custom_outline_w")
    custom_shadow = payload.get("custom_shadow")
    custom_shadow_color = payload.get("custom_shadow_color")
    custom_border_style = payload.get("custom_border_style")
    custom_bg_color = payload.get("custom_bg_color")
    custom_animation = payload.get("custom_animation")
    custom_casing = payload.get("custom_casing")
    custom_chunk_size = payload.get("custom_chunk_size")
    custom_alignment = payload.get("custom_alignment")
    layout = payload.get("layout", "portrait")
    watermark_enabled = bool(payload.get("watermark_enabled", False))
    watermark_text = payload.get("watermark_text", "").strip()
    watermark_pos = payload.get("watermark_pos", "top_right").strip()
    channel_name = payload.get("channel_name", "Cortes Virais").strip()
    channel_handle = payload.get("channel_handle", "@cortesvirais").strip()
    tweet_text = payload.get("tweet_text", "").strip()
    speed = float(payload.get("speed", 1.0))
    enable_zoom = bool(payload.get("enable_zoom", True))
    enable_drift = bool(payload.get("enable_drift", True))
    center_face = bool(payload.get("center_face", True))
    motion_graphics = bool(payload.get("motion_graphics", True))
    sound_effects = bool(payload.get("sound_effects", True))

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
                        channel_name=channel_name,
                        channel_handle=channel_handle,
                        tweet_text=tweet_text,
                        watermark_enabled=watermark_enabled,
                        watermark_text=watermark_text,
                        watermark_pos=watermark_pos,
                        subtitle_style=subtitle_style,
                        custom_color=custom_color,
                        custom_font_size=custom_size,
                        custom_margin_v=custom_margin,
                        custom_highlight_color=custom_highlight_color,
                        custom_font=custom_font,
                        custom_outline_color=custom_outline_color,
                        custom_outline_w=custom_outline_w,
                        custom_shadow=custom_shadow,
                        custom_shadow_color=custom_shadow_color,
                        custom_border_style=custom_border_style,
                        custom_bg_color=custom_bg_color,
                        custom_animation=custom_animation,
                        custom_casing=custom_casing,
                        custom_chunk_size=custom_chunk_size,
                        custom_alignment=custom_alignment,
                        speed=speed,
                        enable_zoom=enable_zoom,
                        enable_drift=enable_drift,
                        center_face=center_face,
                        enable_motion_graphics=motion_graphics,
                        enable_sound_effects=sound_effects,
                        output_file=out_path
                    )
                    c["video_url"] = f"/outputs/{out_filename}"
                    c["filename"] = out_filename
                except Exception as ex:
                    print(f"[Server] Aviso ao renderizar {c_id}: {ex}")
                    try:
                        # Re-tentativa segura garantindo sempre enquadramento 9:16 e legendas sincronizadas
                        video_pipeline.render_viral_cut(
                            source_video=actual_source,
                            cut_info=c,
                            words=words,
                            layout=layout,
                            subtitle_style=subtitle_style,
                            enable_zoom=False,
                            enable_drift=False,
                            enable_sound_effects=False,
                            output_file=out_path
                        )
                        c["video_url"] = f"/outputs/{out_filename}"
                        c["filename"] = out_filename
                    except Exception as ex2:
                        print(f"[Server] Erro na renderização de {c_id}: {ex2}")
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
                "custom_highlight_color": custom_highlight_color,
                "custom_font": custom_font,
                "custom_outline_color": custom_outline_color,
                "custom_outline_w": custom_outline_w,
                "custom_shadow": custom_shadow,
                "custom_shadow_color": custom_shadow_color,
                "custom_border_style": custom_border_style,
                "custom_bg_color": custom_bg_color,
                "custom_animation": custom_animation,
                "custom_casing": custom_casing,
                "custom_chunk_size": custom_chunk_size,
                "custom_alignment": custom_alignment,
                "layout": layout,
                "channel_name": channel_name,
                "channel_handle": channel_handle,
                "tweet_text": tweet_text,
                "watermark_enabled": watermark_enabled,
                "watermark_text": watermark_text,
                "watermark_pos": watermark_pos,
                "speed": speed,
                "enable_zoom": enable_zoom,
                "enable_drift": enable_drift,
                "center_face": center_face,
                "motion_graphics": motion_graphics,
                "sound_effects": sound_effects,
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
                channel_name=project.get("channel_name", "Cortes Virais"),
                channel_handle=project.get("channel_handle", "@cortesvirais"),
                watermark_enabled=project.get("watermark_enabled", False),
                watermark_text=project.get("watermark_text", ""),
                watermark_pos=project.get("watermark_pos", "top_right"),
                subtitle_style=project.get("subtitle_style", "hormozi_pop"),
                custom_color=project.get("custom_color"),
                custom_font_size=project.get("custom_size"),
                custom_margin_v=project.get("custom_margin"),
                speed=project.get("speed", 1.0),
                enable_zoom=project.get("enable_zoom", True),
                enable_drift=project.get("enable_drift", True),
                center_face=project.get("center_face", True),
                enable_motion_graphics=project.get("motion_graphics", True),
                enable_sound_effects=project.get("sound_effects", True),
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

@app.post("/api/cut/update-caption")
async def update_cut_caption(payload: Dict[str, Any]):
    """Atualiza a legenda SEO (texto, emojis e hashtags) do corte."""
    project_id = payload.get("project_id")
    cut_id = payload.get("cut_id")
    caption_seo = payload.get("caption_seo", "").strip()
    title = payload.get("title", "").strip()

    if not project_id or not cut_id:
        raise HTTPException(status_code=400, detail="project_id e cut_id são obrigatórios.")

    project = ACTIVE_PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    target_cut = next((c for c in project.get("cuts", []) if c["id"] == cut_id), None)
    if not target_cut:
        raise HTTPException(status_code=404, detail="Corte não encontrado.")

    from ai_director import sanitize_instagram_caption
    if caption_seo:
        target_cut["caption_seo"] = sanitize_instagram_caption(caption_seo)
    if title:
        target_cut["title"] = title

    return {"success": True, "cut": target_cut}

@app.post("/api/cut/update-subtitles")
async def update_cut_subtitles(payload: Dict[str, Any]):
    """
    Permite corrigir as palavras da legenda do vídeo, trocar estilo/cor e regerar o vídeo 9:16 imediatamente.
    """
    project_id = payload.get("project_id")
    cut_id = payload.get("cut_id")
    edited_text = payload.get("edited_text", "").strip()
    subtitle_style = payload.get("subtitle_style")
    custom_color = payload.get("custom_color")
    custom_size = payload.get("custom_size")
    custom_margin_v = payload.get("custom_margin_v")
    custom_highlight_color = payload.get("custom_highlight_color")
    custom_font = payload.get("custom_font")
    custom_outline_color = payload.get("custom_outline_color")
    custom_outline_w = payload.get("custom_outline_w")
    custom_shadow = payload.get("custom_shadow")
    custom_shadow_color = payload.get("custom_shadow_color")
    custom_border_style = payload.get("custom_border_style")
    custom_bg_color = payload.get("custom_bg_color")
    custom_animation = payload.get("custom_animation")
    custom_casing = payload.get("custom_casing")
    custom_chunk_size = payload.get("custom_chunk_size")
    custom_alignment = payload.get("custom_alignment")

    project = ACTIVE_PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    target_cut = next((c for c in project.get("cuts", []) if c["id"] == cut_id), None)
    if not target_cut:
        raise HTTPException(status_code=404, detail="Corte não encontrado.")

    if subtitle_style:
        target_cut["subtitle_style"] = subtitle_style
    else:
        subtitle_style = target_cut.get("subtitle_style", project.get("subtitle_style", "hormozi_pop"))

    # Salva atributos personalizados no corte
    if custom_color: target_cut["custom_color"] = custom_color
    if custom_highlight_color: target_cut["custom_highlight_color"] = custom_highlight_color
    if custom_font: target_cut["custom_font"] = custom_font
    if custom_size: target_cut["custom_font_size"] = custom_size
    if custom_outline_color: target_cut["custom_outline_color"] = custom_outline_color
    if custom_outline_w is not None: target_cut["custom_outline_w"] = custom_outline_w
    if custom_shadow is not None: target_cut["custom_shadow"] = custom_shadow
    if custom_shadow_color: target_cut["custom_shadow_color"] = custom_shadow_color
    if custom_border_style is not None: target_cut["custom_border_style"] = custom_border_style
    if custom_bg_color: target_cut["custom_bg_color"] = custom_bg_color
    if custom_animation: target_cut["custom_animation"] = custom_animation
    if custom_casing: target_cut["custom_casing"] = custom_casing
    if custom_chunk_size is not None: target_cut["custom_chunk_size"] = custom_chunk_size
    if custom_margin_v is not None: target_cut["custom_margin_v"] = custom_margin_v
    if custom_alignment is not None: target_cut["custom_alignment"] = custom_alignment

    # Converte o texto editado em palavras sincronizadas
    if edited_text:
        target_cut["hook"] = edited_text
        words_raw = edited_text.split()
        dur = max(3.0, target_cut["end"] - target_cut["start"])
        step = dur / max(1, len(words_raw))
        rebuilt_words = []
        for idx, w in enumerate(words_raw):
            s = target_cut["start"] + idx * step
            rebuilt_words.append({
                "word": w,
                "start": round(s, 2),
                "end": round(s + min(step, 0.45), 2)
            })
        target_cut["edited_subtitles"] = rebuilt_words

    out_filename = f"{cut_id}_edited_{uuid.uuid4().hex[:6]}.mp4"
    out_path = os.path.join(video_pipeline.output_dir, out_filename)

    try:
        video_pipeline.render_viral_cut(
            source_video=project["source_url"],
            cut_info=target_cut,
            words=project.get("words", []),
            layout=project.get("layout", "portrait"),
            broll_mode=project.get("broll_mode", "auto_extract"),
            broll_source=project.get("broll_url"),
            subtitle_style=subtitle_style,
            custom_color=custom_color or target_cut.get("custom_color") or project.get("custom_color"),
            custom_font_size=custom_size or target_cut.get("custom_font_size") or project.get("custom_size"),
            custom_margin_v=custom_margin_v or target_cut.get("custom_margin_v") or project.get("custom_margin"),
            custom_highlight_color=custom_highlight_color or target_cut.get("custom_highlight_color") or project.get("custom_highlight_color"),
            custom_font=custom_font or target_cut.get("custom_font") or project.get("custom_font"),
            custom_outline_color=custom_outline_color or target_cut.get("custom_outline_color") or project.get("custom_outline_color"),
            custom_outline_w=custom_outline_w if custom_outline_w is not None else (target_cut.get("custom_outline_w") if target_cut.get("custom_outline_w") is not None else project.get("custom_outline_w")),
            custom_shadow=custom_shadow if custom_shadow is not None else (target_cut.get("custom_shadow") if target_cut.get("custom_shadow") is not None else project.get("custom_shadow")),
            custom_shadow_color=custom_shadow_color or target_cut.get("custom_shadow_color") or project.get("custom_shadow_color"),
            custom_border_style=custom_border_style if custom_border_style is not None else (target_cut.get("custom_border_style") if target_cut.get("custom_border_style") is not None else project.get("custom_border_style")),
            custom_bg_color=custom_bg_color or target_cut.get("custom_bg_color") or project.get("custom_bg_color"),
            custom_animation=custom_animation or target_cut.get("custom_animation") or project.get("custom_animation"),
            custom_casing=custom_casing or target_cut.get("custom_casing") or project.get("custom_casing"),
            custom_chunk_size=custom_chunk_size or target_cut.get("custom_chunk_size") or project.get("custom_chunk_size"),
            custom_alignment=custom_alignment or target_cut.get("custom_alignment") or project.get("custom_alignment"),
            speed=project.get("speed", 1.0),
            enable_zoom=project.get("enable_zoom", True),
            enable_drift=project.get("enable_drift", True),
            center_face=project.get("center_face", True),
            enable_motion_graphics=project.get("motion_graphics", True),
            enable_sound_effects=project.get("sound_effects", True),
            output_file=out_path
        )
        target_cut["video_url"] = f"/outputs/{out_filename}"
        target_cut["filename"] = out_filename
        return {"success": True, "video_url": target_cut["video_url"], "cut": target_cut}
    except Exception as e:
        print(f"[Server] Erro ao regerar corte com legendas corrigidas: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível regerar o vídeo com a nova legenda.")

@app.get("/api/subtitles/presets")
async def get_all_subtitle_presets():
    """Retorna os 24 presets de legendas profissionais com metadados para a interface."""
    from video_pipeline import get_subtitle_presets_dict
    return {"success": True, "presets": get_subtitle_presets_dict()}

@app.get("/api/studio/cut-details")
async def get_studio_cut_details(project_id: str, cut_id: str):
    """Retorna os dados detalhados e as palavras sincronizadas de um corte para o Studio Timeline Editor."""
    project = ACTIVE_PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    target_cut = next((c for c in project.get("cuts", []) if c["id"] == cut_id), None)
    if not target_cut:
        raise HTTPException(status_code=404, detail="Corte não encontrado.")

    c_start = float(target_cut.get("start", 0))
    c_end = float(target_cut.get("end", 0))

    words = target_cut.get("edited_subtitles")
    if not words or not isinstance(words, list) or len(words) == 0:
        all_words = project.get("words", [])
        words = [w for w in all_words if w.get("start", 0) >= (c_start - 0.5) and w.get("end", 0) <= (c_end + 0.5)]

    if not words and (target_cut.get("hook") or target_cut.get("title")):
        raw_text = target_cut.get("hook") or target_cut.get("title") or ""
        raw_w = [w for w in raw_text.split() if w.strip()]
        if raw_w:
            dur = max(3.0, c_end - c_start)
            step = dur / max(1, len(raw_w))
            words = [{"word": w, "start": round(c_start + i * step, 2), "end": round(c_start + (i + 1) * step, 2)} for i, w in enumerate(raw_w)]

    return {
        "success": True,
        "cut": target_cut,
        "words": words or [],
        "source_url": project.get("source_url")
    }

@app.post("/api/studio/render-custom-cut")
async def render_studio_custom_cut(payload: Dict[str, Any]):
    """
    Re-renderiza o corte no Studio Timeline Editor com:
    - Escala e enquadramento visual customizado
    - Toggle de Zoom dinâmico no corte (ativado ou desativado)
    - Estilo e cores de legendas
    - Falas corrigidas e sincronizadas
    """
    project_id = payload.get("project_id")
    cut_id = payload.get("cut_id")
    enable_zoom = bool(payload.get("enable_zoom", True))
    subtitle_style = payload.get("subtitle_style", "hormozi_pop")
    custom_highlight = payload.get("custom_highlight")
    edited_subtitles = payload.get("edited_subtitles")

    if not project_id or not cut_id:
        raise HTTPException(status_code=400, detail="project_id e cut_id são obrigatórios.")

    project = ACTIVE_PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    target_cut = next((c for c in project.get("cuts", []) if c["id"] == cut_id), None)
    if not target_cut:
        raise HTTPException(status_code=404, detail="Corte não encontrado.")

    layout = payload.get("layout", target_cut.get("layout", project.get("layout", "portrait")))
    watermark_enabled = bool(payload.get("watermark_enabled", target_cut.get("watermark_enabled", project.get("watermark_enabled", False))))
    watermark_text = payload.get("watermark_text", target_cut.get("watermark_text", project.get("watermark_text", "")))
    watermark_pos = payload.get("watermark_pos", target_cut.get("watermark_pos", project.get("watermark_pos", "top_right")))
    channel_name = payload.get("channel_name", target_cut.get("channel_name", project.get("channel_name", "Cortes Virais")))
    channel_handle = payload.get("channel_handle", target_cut.get("channel_handle", project.get("channel_handle", "@cortesvirais")))
    tweet_text = payload.get("tweet_text", target_cut.get("tweet_text", target_cut.get("hook", "")))

    target_cut["enable_zoom"] = enable_zoom
    target_cut["subtitle_style"] = subtitle_style
    target_cut["layout"] = layout
    target_cut["watermark_enabled"] = watermark_enabled
    target_cut["watermark_text"] = watermark_text
    target_cut["watermark_pos"] = watermark_pos
    target_cut["channel_name"] = channel_name
    target_cut["channel_handle"] = channel_handle
    if custom_highlight:
        target_cut["custom_highlight_color"] = custom_highlight

    if edited_subtitles and isinstance(edited_subtitles, list):
        target_cut["edited_subtitles"] = edited_subtitles

    out_filename = f"{cut_id}_studio_{uuid.uuid4().hex[:6]}.mp4"
    out_path = os.path.join(video_pipeline.output_dir, out_filename)

    try:
        video_pipeline.render_viral_cut(
            source_video=project["source_url"],
            cut_info=target_cut,
            words=target_cut.get("edited_subtitles") or project.get("words", []),
            layout=layout,
            channel_name=channel_name,
            channel_handle=channel_handle,
            tweet_text=tweet_text,
            watermark_enabled=watermark_enabled,
            watermark_text=watermark_text,
            watermark_pos=watermark_pos,
            subtitle_style=subtitle_style,
            custom_highlight_color=custom_highlight or target_cut.get("custom_highlight_color"),
            enable_zoom=enable_zoom,
            output_file=out_path
        )
        target_cut["video_url"] = f"/outputs/{out_filename}"
        target_cut["filename"] = out_filename
        return {"success": True, "video_url": target_cut["video_url"], "cut": target_cut}
    except Exception as e:
        print(f"[Server] Erro no Studio render: {e}")
        raise HTTPException(status_code=500, detail="Falha ao renderizar edições do Studio.")

@app.post("/api/project/thumbnails")
async def generate_project_thumbnails(payload: Dict[str, Any]):
    """
    Gera o pacote de 3 Thumbnails Virais para YouTube (1280x720) com Extrema Qualidade:
    - Recorte de pessoa em alta definição com contorno profissional
    - Busca de pôster/capa da obra/livro/série/filme ou assunto
    - 3 Estratégias Visuais (Choque, Mistério/VS e Neo-Brutalist)
    - Clickscore (0-100) com análise de CTR
    """
    project_id = payload.get("project_id")
    cut_id = payload.get("cut_id")
    custom_subject = payload.get("subject", "").strip()

    project = ACTIVE_PROJECTS.get(project_id)
    if not project:
        source_url = payload.get("source_url")
        if not source_url:
            raise HTTPException(status_code=404, detail="Projeto ou vídeo não localizado.")
        actual_source = source_url
        video_title = payload.get("title", "Vídeo Selecionado")
        target_cut = None
        cut_timestamp = 12.0
    else:
        actual_source = project["source_url"]
        video_title = project.get("title", "Vídeo Selecionado")
        target_cut = next((c for c in project.get("cuts", []) if c["id"] == cut_id), None) if cut_id else (project.get("cuts", [])[0] if project.get("cuts") else None)
        if target_cut:
            c_dur = max(3.0, target_cut.get("end", 30.0) - target_cut.get("start", 0.0))
            cut_timestamp = target_cut.get("start", 0.0) + min(6.0, c_dur * 0.25)
            base_x = target_cut.get("base_x")
        else:
            cut_timestamp = 12.0
            base_x = None

    topic_data = ai_director.generate_thumbnail_strategy(
        video_title=video_title,
        cut_info=target_cut
    )
    if custom_subject:
        topic_data["subject"] = custom_subject
        topic_data["search_query"] = f"{custom_subject} book movie poster"

    thumbs = thumbnail_generator.generate_thumbnails_pack(
        video_path=actual_source,
        topic_data=topic_data,
        cut_timestamp=cut_timestamp,
        base_x=base_x
    )

    return {
        "success": True,
        "subject": topic_data.get("subject", video_title),
        "thumbnails": thumbs
    }

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
