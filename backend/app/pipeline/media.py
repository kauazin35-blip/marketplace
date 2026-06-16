"""Entrada de mídia: download do YouTube e extração de áudio.

- `download_youtube`: baixa um vídeo via yt-dlp.
- `extract_audio`: extrai faixa de áudio 16kHz mono (formato ideal p/ Whisper).
- `probe_duration`: descobre a duração do vídeo via ffprobe.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def _require(binary: str) -> None:
    if shutil.which(binary) is None:
        raise RuntimeError(
            f"'{binary}' não encontrado no sistema. Instale o ffmpeg "
            f"(inclui ffprobe) e garanta que está no PATH."
        )


def download_youtube(url: str, dest_dir: Path, job_id: str) -> Path:
    """Baixa um vídeo do YouTube (ou outro site suportado pelo yt-dlp)."""
    import yt_dlp

    out_template = str(dest_dir / f"{job_id}_source.%(ext)s")
    ydl_opts = {
        # Prioriza mp4 já mesclado; cai para o melhor disponível.
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        downloaded = Path(ydl.prepare_filename(info))

    # yt-dlp pode trocar a extensão após o merge; procura o arquivo real.
    if not downloaded.exists():
        candidates = sorted(dest_dir.glob(f"{job_id}_source.*"))
        if not candidates:
            raise RuntimeError("Falha ao baixar o vídeo do YouTube.")
        downloaded = candidates[0]
    return downloaded


def extract_audio(video_path: Path, dest_dir: Path, job_id: str) -> Path:
    """Extrai áudio 16kHz mono WAV (o que o Whisper espera)."""
    _require("ffmpeg")
    audio_path = dest_dir / f"{job_id}_audio.wav"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(audio_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return audio_path


def probe_duration(video_path: Path) -> float:
    """Duração do vídeo em segundos (via ffprobe)."""
    _require("ffprobe")
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])
