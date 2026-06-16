"""Renderização final de cada corte.

Para cada ClipPlan: corta o trecho, reenquadra para 9:16 seguindo o rosto
e (opcionalmente) queima as legendas — tudo em uma passada do ffmpeg.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

from ..config import settings
from ..schemas import Segment, ClipPlan, Clip
from . import reframe, captions


def _probe_dims(video_path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "v:0", str(video_path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    stream = json.loads(result.stdout)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def _ass_path_for_filter(path: Path) -> str:
    """Escapa o caminho do .ass para uso dentro do filtro do ffmpeg."""
    p = str(path.resolve())
    # No Windows é preciso escapar ':' e '\' dentro do filtergraph.
    p = p.replace("\\", "/").replace(":", "\\:")
    return p


def render_clip(video_path: Path, segments: list[Segment], plan: ClipPlan,
                job_id: str, index: int) -> Clip:
    src_w, src_h = _probe_dims(video_path)
    crop_x = reframe.compute_crop_x(video_path, plan.start, plan.end)
    vf = reframe.crop_filter(src_w, src_h, crop_x)

    clip_id = uuid.uuid4().hex[:8]
    filename = f"{job_id}_clip{index:02d}_{clip_id}.mp4"
    out_path = settings.output_dir / filename
    duration = plan.end - plan.start

    # Legendas (opcional).
    ass_file: Path | None = None
    if settings.burn_captions:
        ass_file = captions.build_ass(
            segments, plan.start, plan.end,
            settings.data_dir / f"{job_id}_clip{index:02d}.ass",
        )
    if ass_file is not None:
        vf = f"{vf},subtitles='{_ass_path_for_filter(ass_file)}'"

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{plan.start:.3f}",
        "-i", str(video_path),
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    # Limpa o .ass temporário.
    if ass_file is not None:
        ass_file.unlink(missing_ok=True)

    return Clip(
        **plan.model_dump(),
        id=clip_id,
        filename=filename,
        url=f"/clips/{filename}",
        duration=round(duration, 2),
    )


def render_all(video_path: Path, segments: list[Segment],
               plans: list[ClipPlan], job_id: str,
               on_progress=None) -> list[Clip]:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg não encontrado no PATH.")

    clips: list[Clip] = []
    total = len(plans)
    for i, plan in enumerate(plans, start=1):
        try:
            clips.append(render_clip(video_path, segments, plan, job_id, i))
        except subprocess.CalledProcessError:
            # Um corte com erro não derruba o lote inteiro.
            continue
        if on_progress:
            on_progress(i, total)
    return clips
