"""Reframe para 9:16 seguindo o rosto do falante.

Analisa alguns quadros do trecho com OpenCV (detecção de rosto Haar),
calcula o centro horizontal médio onde está a ação e devolve a posição
de corte (crop) para o ffmpeg. Se não achar rosto, usa corte central.
"""
from __future__ import annotations

from pathlib import Path

import cv2

from ..config import settings


def compute_crop_x(video_path: Path, clip_start: float, clip_end: float) -> float:
    """Retorna a fração horizontal (0..1) onde centralizar o corte 9:16."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return 0.5

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920.0

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    # Amostra ~8 quadros ao longo do trecho.
    duration = max(0.1, clip_end - clip_start)
    samples = 8
    centers: list[float] = []

    for i in range(samples):
        t = clip_start + duration * (i + 0.5) / samples
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
        if len(faces) == 0:
            continue
        # Maior rosto = falante principal.
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        centers.append((x + fw / 2.0) / width)

    cap.release()

    if not centers:
        return 0.5
    return sum(centers) / len(centers)


def crop_filter(src_w: int, src_h: int, crop_x_frac: float) -> str:
    """Monta o filtro ffmpeg de crop+scale para 9:16, centralizado no rosto."""
    out_w, out_h = settings.out_width, settings.out_height
    target_ratio = out_w / out_h  # 9/16

    # Largura do recorte mantendo a altura total do vídeo.
    crop_w = int(src_h * target_ratio)
    crop_w = min(crop_w, src_w)

    center_px = crop_x_frac * src_w
    x = int(center_px - crop_w / 2)
    x = max(0, min(x, src_w - crop_w))

    return (
        f"crop={crop_w}:{src_h}:{x}:0,"
        f"scale={out_w}:{out_h}:flags=lanczos"
    )
