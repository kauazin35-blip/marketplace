"""Transcrição de áudio com faster-whisper (GPU/CUDA).

Carrega o modelo uma única vez (cache global) e devolve segmentos com
timestamps por palavra — essenciais para legendas e para a IA escolher cortes.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from ..config import settings
from ..schemas import Segment, Word


@lru_cache(maxsize=1)
def _load_model():
    """Carrega o modelo Whisper (cacheado). Cai para CPU se a GPU falhar."""
    from faster_whisper import WhisperModel

    try:
        return WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    except Exception:
        # Fallback robusto: sem CUDA disponível, roda na CPU.
        return WhisperModel(
            settings.whisper_model,
            device="cpu",
            compute_type="int8",
        )


def transcribe(audio_path: Path, language: str | None = None) -> list[Segment]:
    """Transcreve o áudio e retorna segmentos com palavras temporizadas."""
    model = _load_model()
    lang = language or settings.whisper_language

    segments_iter, _info = model.transcribe(
        str(audio_path),
        language=lang,
        word_timestamps=True,
        vad_filter=True,  # remove silêncios -> timestamps mais limpos
    )

    segments: list[Segment] = []
    for seg in segments_iter:
        words = [
            Word(start=w.start, end=w.end, text=w.word)
            for w in (seg.words or [])
            if w.start is not None and w.end is not None
        ]
        segments.append(
            Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                words=words,
            )
        )
    return segments


def full_text(segments: list[Segment]) -> str:
    return " ".join(s.text for s in segments).strip()
