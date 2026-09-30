import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import json
import time
import uuid
import threading
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from ai_director import AIDirector
from audio_ingest import AudioIngestEngine
from video_pipeline import VideoPipeline

app = FastAPI(title="Cortefy AI", version="2.0.0")

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

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    response = HTMLResponse(content=content)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/api/health")
async def health_check():
    ai_ready = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "online",
        "service": "Cortefy",
        "ready": ai_ready,
        "version": "2.7.0",
        "timestamp": time.time()
    }

@app.get("/api/monthly-stats")
async def get_monthly_stats():
    return MONTHLY_USAGE

@app.post("/api/monthly-stats/increment")
async def increment_monthly_stats():
    MONTHLY_USAGE["used"] = min(MONTHLY_USAGE["limit"], MONTHLY_USAGE["used"] + 1)
    return MONTHLY_USAGE

@app.get("/api/video-info")
async def get_video_info(url: str):
    """Retorna metadados do vídeo para a prévia instantânea (título, capa, duração)."""
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
                (45, "Identificando as falas e ritmo da conversa..."),
                (60, "Calculando o potencial de retenção e ganchos virais..."),
                (80, "Criando títulos irresistíveis e legendas com SEO..."),
                (92, "Quase pronto, organizando os 5 melhores cortes...")
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
                update_progress(30, "Vídeo já memorizado! Encontrando cortes virais...")
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
                    update_progress(50, "Avaliando momentos com maior potencial viral...")
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

                update_progress(60, "Identificando os melhores momentos...")
                cuts = ai_director.analyze_audio_directly(audio_path, video_title=video_title, genre=genre)

                if not cuts:
                    ingest_res = audio_engine.transcribe_audio_file(audio_path, video_title=video_title, progress_callback=update_progress)
                    cuts = ai_director.analyze_virality(ingest_res["segments"], video_title=video_title, genre=genre)
                    words = ingest_res.get("words", [])

            heartbeat_running = False

            # Salva o projeto
            project_id = f"proj_{uuid.uuid4().hex[:6]}"
            ACTIVE_PROJECTS[project_id] = {
                "source_url": source_url,
                "broll_mode": broll_mode,
                "broll_url": broll_url,
                "genre": genre,
                "title": video_title,
                "duration": 0,
                "words": words,
                "cuts": cuts
            }

            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["progress"] = 100
            TASKS[task_id]["message"] = f"Pronto! Encontramos {len(cuts)} cortes virais ranqueados."
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
    """Gera mais 5 cortes virais sem reprocessar o vídeo do zero."""
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
        new_cuts = ai_director._heuristic_fallback([{"end": 600.0}], batch_index=batch_idx)

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

    # Incrementa contador mensal
    MONTHLY_USAGE["used"] = min(MONTHLY_USAGE["limit"], MONTHLY_USAGE["used"] + 1)

    render_task_id = f"render_{uuid.uuid4().hex[:8]}"
    TASKS[render_task_id] = {
        "status": "processing",
        "progress": 5,
        "message": "Preparando fatiamento e enquadramento...",
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
    print(f"\n⚡ [CORTEFY AI] Servidor iniciado em http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)
