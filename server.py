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

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/health")
async def health_check():
    gemini_key_set = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "online",
        "service": "Cortefy AI Core",
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        "gemini_authenticated": gemini_key_set,
        "engine_version": "2.4.0",
        "audio_first_ingestion": True,
        "dual_broll_mode": True,
        "timestamp": time.time()
    }

@app.post("/api/project/analyze")
async def start_analysis(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    source_url = payload.get("source_url", "").strip()
    broll_mode = payload.get("broll_mode", "auto_extract")
    broll_url = payload.get("broll_url", "").strip()

    if not source_url:
        # Se nenhuma URL foi passada, usa o vídeo padrão de amostra existente
        sample_path = os.path.join(os.path.dirname(BASE_DIR), "video_source.mp4")
        if os.path.exists(sample_path):
            source_url = sample_path
        else:
            raise HTTPException(status_code=400, detail="Por favor, forneça uma URL válida do YouTube ou arquivo.")

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    TASKS[task_id] = {
        "status": "processing",
        "progress": 5,
        "message": "Inicializando pipeline Audio-First...",
        "result": None,
        "error": None
    }

    def process_task():
        try:
            def update_progress(prog: int, msg: str):
                TASKS[task_id]["progress"] = prog
                TASKS[task_id]["message"] = msg

            # 1. Ingestão de Áudio
            update_progress(10, "Baixando áudio ultra-compacto em segundos...")
            if source_url.startswith("http://") or source_url.startswith("https://"):
                ingest_res = audio_engine.ingest_youtube_audio(source_url, progress_callback=update_progress)
            else:
                ingest_res = audio_engine.extract_audio_from_local_file(source_url, progress_callback=update_progress)

            # 2. Análise com Gemini 3.6 Flash
            update_progress(88, "Diretor de Criação Gemini 3.6 Flash identificando ganchos virais...")
            cuts = ai_director.analyze_virality(ingest_res["segments"], video_title=ingest_res.get("title", ""))

            # Salva o projeto
            project_id = f"proj_{uuid.uuid4().hex[:6]}"
            ACTIVE_PROJECTS[project_id] = {
                "source_url": source_url,
                "broll_mode": broll_mode,
                "broll_url": broll_url,
                "title": ingest_res.get("title", "Projeto"),
                "duration": ingest_res.get("duration", 0),
                "words": ingest_res.get("words", []),
                "cuts": cuts
            }

            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["progress"] = 100
            TASKS[task_id]["message"] = f"Análise concluída! {len(cuts)} cortes virais identificados."
            TASKS[task_id]["result"] = {
                "project_id": project_id,
                "title": ingest_res.get("title", "Projeto"),
                "duration": ingest_res.get("duration", 0),
                "cuts": cuts
            }
        except Exception as e:
            TASKS[task_id]["status"] = "error"
            TASKS[task_id]["error"] = str(e)
            TASKS[task_id]["message"] = f"Falha na análise: {str(e)[:150]}"

    threading.Thread(target=process_task, daemon=True).start()
    return {"task_id": task_id}

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
    subtitle_style = payload.get("subtitle_style", "yellow_viral")
    speed = float(payload.get("speed", 1.05))
    broll_mode = payload.get("broll_mode", "auto_extract")
    broll_source = payload.get("broll_source")

    project = ACTIVE_PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    selected_cut = next((c for c in project["cuts"] if c["id"] == cut_id), None)
    if not selected_cut:
        raise HTTPException(status_code=404, detail="Corte não encontrado.")

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
                speed=speed,
                progress_cb=update_cb
            )

            fname = os.path.basename(out_file)
            TASKS[render_task_id]["status"] = "completed"
            TASKS[render_task_id]["progress"] = 100
            TASKS[render_task_id]["message"] = "Renderização concluída com sucesso!"
            TASKS[render_task_id]["filename"] = fname
            TASKS[render_task_id]["output_url"] = f"/outputs/{fname}"
        except Exception as e:
            TASKS[render_task_id]["status"] = "error"
            TASKS[render_task_id]["error"] = str(e)
            TASKS[render_task_id]["message"] = f"Erro ao renderizar: {str(e)[:150]}"

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
