"""IA de cortes — o "cérebro" estilo OpusClip.

Recebe a transcrição (com timestamps) e escolhe os melhores momentos
virais com base em GANCHOS e TEMAS. Estratégia em camadas:

1. Ollama (local, offline)  -> padrão
2. Claude API (se configurado) -> fallback opcional
3. Heurística (sempre funciona) -> rede de segurança se não houver LLM

Saída: lista de ClipPlan com start/end/título/gancho/tema/score.
"""
from __future__ import annotations

import json
import re

import httpx

from ..config import settings
from ..schemas import Segment, ClipPlan


# ---------------------------------------------------------------------------
# Prompt compartilhado
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Você é um editor especialista em vídeos virais para TikTok, Reels e Shorts. "
    "Seu trabalho é ler a transcrição de um vídeo longo (com tempos em segundos) "
    "e selecionar os MELHORES trechos para virarem cortes verticais virais. "
    "Priorize trechos com GANCHO forte (algo que prende nos primeiros segundos), "
    "uma ideia ou história completa, emoção, polêmica, dicas práticas ou viradas. "
    "Cada corte deve começar e terminar em fronteiras naturais de fala."
)


def _build_user_prompt(segments: list[Segment], max_clips: int) -> str:
    lines = []
    for s in segments:
        lines.append(f"[{s.start:.1f} - {s.end:.1f}] {s.text}")
    transcript = "\n".join(lines)

    return (
        f"Transcrição do vídeo (tempos em segundos):\n\n{transcript}\n\n"
        f"Selecione até {max_clips} cortes. Cada corte deve ter entre "
        f"{settings.clip_min_seconds} e {settings.clip_max_seconds} segundos.\n\n"
        "Responda SOMENTE com um JSON válido neste formato exato:\n"
        '{\n'
        '  "clips": [\n'
        '    {\n'
        '      "start": 12.3,\n'
        '      "end": 48.7,\n'
        '      "title": "Título curto e chamativo",\n'
        '      "hook": "A primeira frase que prende a atenção",\n'
        '      "theme": "Tema/assunto do corte",\n'
        '      "virality_score": 87,\n'
        '      "reason": "Por que este trecho tem potencial viral"\n'
        '    }\n'
        '  ]\n'
        "}\n"
        "Não escreva nada fora do JSON."
    )


# ---------------------------------------------------------------------------
# Provedores
# ---------------------------------------------------------------------------

def _ask_ollama(system: str, user: str) -> str:
    """Chama o Ollama local. Retorna o texto bruto da resposta."""
    resp = httpx.post(
        f"{settings.ollama_url}/api/chat",
        json={
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.4},
        },
        timeout=600,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _ask_claude(system: str, user: str) -> str:
    """Fallback via API da Anthropic (Claude). Requer ANTHROPIC_API_KEY."""
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.anthropic_api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.claude_model,
            "max_tokens": 4000,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=600,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(b["text"] for b in data["content"] if b["type"] == "text")


# ---------------------------------------------------------------------------
# Parsing + heurística de segurança
# ---------------------------------------------------------------------------

def _parse_clips(raw: str) -> list[ClipPlan]:
    """Extrai o JSON da resposta do LLM de forma tolerante."""
    # Tenta achar o primeiro bloco { ... } caso venha texto em volta.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    blob = match.group(0) if match else raw
    data = json.loads(blob)
    items = data.get("clips", data if isinstance(data, list) else [])

    clips: list[ClipPlan] = []
    for it in items:
        try:
            clips.append(
                ClipPlan(
                    start=float(it["start"]),
                    end=float(it["end"]),
                    title=str(it.get("title", "Corte")).strip(),
                    hook=str(it.get("hook", "")).strip(),
                    theme=str(it.get("theme", "")).strip(),
                    virality_score=int(it.get("virality_score", 0)),
                    reason=str(it.get("reason", "")).strip(),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return clips


def _heuristic_clips(segments: list[Segment], max_clips: int) -> list[ClipPlan]:
    """Rede de segurança: divide o vídeo em blocos coerentes por duração."""
    clips: list[ClipPlan] = []
    if not segments:
        return clips

    target = (settings.clip_min_seconds + settings.clip_max_seconds) / 2

    def _flush(start: float, end: float, texts: list[str]) -> None:
        clips.append(
            ClipPlan(
                start=start,
                end=end,
                title=" ".join(texts)[:60] or "Corte",
                hook=texts[0] if texts else "",
                theme="auto",
                virality_score=50,
                reason="Selecionado por divisão automática (sem LLM).",
            )
        )

    bucket_start = segments[0].start
    bucket_text: list[str] = []
    last_end = segments[0].end

    for seg in segments:
        bucket_text.append(seg.text)
        last_end = seg.end
        if seg.end - bucket_start >= target:
            _flush(bucket_start, seg.end, bucket_text)
            bucket_start = seg.end
            bucket_text = []
        if len(clips) >= max_clips:
            break

    # Fecha o último bloco restante (cobre vídeos mais curtos que o alvo).
    if bucket_text and len(clips) < max_clips:
        _flush(bucket_start, last_end, bucket_text)

    return clips


def _sanitize(clips: list[ClipPlan], total_duration: float) -> list[ClipPlan]:
    """Garante limites de duração e fronteiras válidas; ordena por score."""
    out: list[ClipPlan] = []
    for c in clips:
        start = max(0.0, min(c.start, total_duration))
        end = max(start + 1.0, min(c.end, total_duration))
        dur = end - start
        if dur < settings.clip_min_seconds * 0.6:
            continue
        if dur > settings.clip_max_seconds:
            end = start + settings.clip_max_seconds
        c.start, c.end = start, end
        out.append(c)
    out.sort(key=lambda x: x.virality_score, reverse=True)
    return out


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def analyze(segments: list[Segment], total_duration: float,
            max_clips: int | None = None) -> list[ClipPlan]:
    max_clips = max_clips or settings.max_clips
    system = SYSTEM_PROMPT
    user = _build_user_prompt(segments, max_clips)

    raw: str | None = None
    try:
        if settings.llm_provider == "claude" and settings.anthropic_api_key:
            raw = _ask_claude(system, user)
        else:
            raw = _ask_ollama(system, user)
    except Exception:
        raw = None

    clips: list[ClipPlan] = []
    if raw:
        try:
            clips = _parse_clips(raw)
        except Exception:
            clips = []

    if not clips:
        clips = _heuristic_clips(segments, max_clips)

    clips = _sanitize(clips, total_duration)
    return clips[:max_clips]
