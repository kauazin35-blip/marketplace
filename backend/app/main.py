"""API FastAPI do cortador de vídeo automático.

Rotas:
  POST /api/jobs            -> cria job (upload de arquivo OU link do YouTube)
  GET  /api/jobs/{id}       -> status + cortes do job
  GET  /api/jobs            -> lista todos os jobs
  GET  /api/health          -> checa ffmpeg, GPU e LLM
  GET  /clips/{arquivo}     -> baixa um corte renderizado
  GET  /                    -> frontend (site)
"""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings, ROOT_DIR
from .jobs import manager
from .schemas import Job

app = FastAPI(title="Cortador de Vídeo Automático", version="1.0.0")

FRONTEND_DIR = ROOT_DIR / "frontend"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    import httpx

    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ffprobe_ok = shutil.which("ffprobe") is not None

    gpu = False
    try:
        import torch  # type: ignore
        gpu = bool(torch.cuda.is_available())
    except Exception:
        gpu = None  # torch não instalado; faster-whisper traz seu próprio runtime

    llm_ok = False
    if settings.llm_provider == "claude":
        llm_ok = bool(settings.anthropic_api_key)
    else:
        try:
            r = httpx.get(f"{settings.ollama_url}/api/tags", timeout=2)
            llm_ok = r.status_code == 200
        except Exception:
            llm_ok = False

    return {
        "ffmpeg": ffmpeg_ok,
        "ffprobe": ffprobe_ok,
        "gpu_cuda": gpu,
        "llm_provider": settings.llm_provider,
        "llm_ready": llm_ok,
        "whisper_model": settings.whisper_model,
        "whisper_device": settings.whisper_device,
    }


@app.post("/api/jobs", response_model=Job)
async def create_job(
    file: UploadFile | None = File(default=None),
    youtube_url: str | None = Form(default=None),
    language: str | None = Form(default=None),
    max_clips: int | None = Form(default=None),
) -> Job:
    if not file and not youtube_url:
        raise HTTPException(400, "Envie um arquivo de vídeo ou um link do YouTube.")

    video_path: Path | None = None
    source = youtube_url or ""

    if file:
        suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
        job = manager.create(source=file.filename or "upload")
        video_path = settings.data_dir / f"{job.id}_source{suffix}"
        with video_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    else:
        job = manager.create(source=source)

    manager.start(job.id, video_path, youtube_url, language, max_clips)
    return job


@app.get("/api/jobs/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    job = manager.get(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado.")
    return job


@app.get("/api/jobs", response_model=list[Job])
def list_jobs() -> list[Job]:
    return manager.all()


@app.get("/clips/{filename}")
def download_clip(filename: str) -> FileResponse:
    # Evita path traversal: usa só o nome base.
    safe = Path(filename).name
    path = settings.output_dir / safe
    if not path.exists():
        raise HTTPException(404, "Corte não encontrado.")
    return FileResponse(path, media_type="video/mp4", filename=safe)


# ---------------------------------------------------------------------------
# Frontend (site) — montado por último para não cobrir as rotas /api
# ---------------------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="site")
