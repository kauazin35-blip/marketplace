"""Gerenciador de jobs em memória + execução do pipeline em thread.

Cada upload/URL vira um Job. O processamento roda numa thread separada para
não travar a API, e o status é atualizado em tempo real (consultável via /jobs).
"""
from __future__ import annotations

import threading
import traceback
import uuid
from pathlib import Path

from .config import settings
from .schemas import Job, JobStatus
from .pipeline import media, transcribe, analyze, render


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    # ----- CRUD básico -----
    def create(self, source: str) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, source=source, status=JobStatus.queued)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def all(self) -> list[Job]:
        return list(self._jobs.values())

    def _update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in fields.items():
                setattr(job, k, v)

    # ----- Execução -----
    def start(self, job_id: str, video_path: Path | None,
              youtube_url: str | None, language: str | None,
              max_clips: int | None) -> None:
        t = threading.Thread(
            target=self._run,
            args=(job_id, video_path, youtube_url, language, max_clips),
            daemon=True,
        )
        t.start()

    def _run(self, job_id: str, video_path: Path | None,
             youtube_url: str | None, language: str | None,
             max_clips: int | None) -> None:
        try:
            # 1) Obter o vídeo
            if youtube_url:
                self._update(job_id, status=JobStatus.downloading, progress=5,
                             message="Baixando vídeo do YouTube...")
                video_path = media.download_youtube(
                    youtube_url, settings.data_dir, job_id)

            assert video_path is not None
            total_duration = media.probe_duration(video_path)

            # 2) Extrair áudio
            self._update(job_id, status=JobStatus.transcribing, progress=20,
                         message="Extraindo áudio...")
            audio_path = media.extract_audio(
                video_path, settings.data_dir, job_id)

            # 3) Transcrever (GPU)
            self._update(job_id, progress=35,
                         message="Transcrevendo (Whisper na GPU)...")
            segments = transcribe.transcribe(audio_path, language)
            preview = transcribe.full_text(segments)[:400]
            self._update(job_id, transcript_preview=preview)

            # 4) IA escolhe os cortes
            self._update(job_id, status=JobStatus.analyzing, progress=55,
                         message="IA analisando ganchos e temas...")
            plans = analyze.analyze(segments, total_duration, max_clips)
            if not plans:
                raise RuntimeError("Nenhum corte foi gerado pela análise.")

            # 5) Renderizar cortes
            self._update(job_id, status=JobStatus.rendering, progress=65,
                         message=f"Renderizando {len(plans)} cortes...")

            def on_progress(done: int, total: int) -> None:
                pct = 65 + int(30 * done / max(1, total))
                self._update(job_id, progress=pct,
                             message=f"Renderizando corte {done}/{total}...")

            clips = render.render_all(
                video_path, segments, plans, job_id, on_progress)

            if not clips:
                raise RuntimeError("Falha ao renderizar os cortes.")

            self._update(job_id, status=JobStatus.done, progress=100,
                         message=f"{len(clips)} cortes prontos!", clips=clips)

            # Limpeza do áudio temporário.
            try:
                audio_path.unlink(missing_ok=True)
            except Exception:
                pass

        except Exception as exc:  # noqa: BLE001
            self._update(
                job_id,
                status=JobStatus.error,
                error=f"{exc}",
                message="Erro no processamento.",
            )
            traceback.print_exc()


manager = JobManager()
