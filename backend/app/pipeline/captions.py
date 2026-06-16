"""Geração de legendas estilo viral (queimadas no vídeo).

Cria um arquivo .ass com blocos curtos (poucas palavras), grandes e
centralizados — o visual "punchy" típico de Reels/TikTok/OpusClip.
Os tempos vêm das palavras do Whisper, relativos ao início do corte.
"""
from __future__ import annotations

from pathlib import Path

from ..config import settings
from ..schemas import Segment, Word


def _fmt_time(seconds: float) -> str:
    """Formata segundos no padrão ASS: H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs == 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape(text: str) -> str:
    return text.replace("\n", " ").replace("{", "(").replace("}", ")").strip()


def _words_in_range(segments: list[Segment], start: float, end: float) -> list[Word]:
    """Coleta todas as palavras dentro da janela do corte, com tempo relativo."""
    words: list[Word] = []
    for seg in segments:
        for w in seg.words:
            if w.end <= start or w.start >= end:
                continue
            words.append(
                Word(
                    start=max(0.0, w.start - start),
                    end=max(0.0, w.end - start),
                    text=w.text.strip(),
                )
            )
    return words


def build_ass(segments: list[Segment], clip_start: float, clip_end: float,
              out_path: Path) -> Path | None:
    """Monta o .ass para um corte. Retorna None se não houver palavras."""
    words = _words_in_range(segments, clip_start, clip_end)
    if not words:
        return None

    w, h = settings.out_width, settings.out_height
    # Fonte proporcional à largura; margem inferior generosa.
    font_size = int(w * 0.085)
    margin_v = int(h * 0.18)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Viral,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Agrupa palavras em blocos curtos (ex.: 3 palavras).
    chunk_size = max(1, settings.caption_words_per_chunk)
    events: list[str] = []
    for i in range(0, len(words), chunk_size):
        group = words[i:i + chunk_size]
        start = group[0].start
        end = group[-1].end
        if end <= start:
            end = start + 0.4
        text = _escape(" ".join(g.text for g in group)).upper()
        events.append(
            f"Dialogue: 0,{_fmt_time(start)},{_fmt_time(end)},Viral,,0,0,0,,{text}"
        )

    out_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return out_path
