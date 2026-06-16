"""Configuração central do cortador de vídeo.

Tudo é controlado por variáveis de ambiente (ver .env.example).
Os padrões são pensados para uma máquina com GPU NVIDIA (RTX 5070)
e CPU Intel Core Ultra 7, rodando 100% offline.
"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Raiz do projeto: .../marketplace
ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Pastas de trabalho ---
    data_dir: Path = ROOT_DIR / "data"          # uploads + áudio temporário
    output_dir: Path = ROOT_DIR / "data" / "clips"  # cortes finais

    # --- Transcrição (faster-whisper) ---
    # Modelos: tiny, base, small, medium, large-v3 (mais preciso = mais lento)
    whisper_model: str = "large-v3"
    # "cuda" usa a GPU (recomendado p/ 5070). "cpu" como fallback.
    whisper_device: str = "cuda"
    # "float16" na GPU; "int8" na CPU.
    whisper_compute_type: str = "float16"
    # Idioma fixo ("pt") ou None para detectar automaticamente.
    whisper_language: str | None = None

    # --- IA de cortes ---
    # "ollama" (local, offline) ou "claude" (API, precisa de chave).
    llm_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    # Modelo no Ollama. Bom equilíbrio p/ 5070: qwen2.5:7b ou llama3.1:8b
    ollama_model: str = "qwen2.5:7b"
    # Fallback opcional p/ Claude (só usado se llm_provider="claude").
    anthropic_api_key: str | None = None
    claude_model: str = "claude-opus-4-8"

    # --- Geração de cortes ---
    # Quantos cortes gerar por vídeo (a IA escolhe os melhores momentos).
    max_clips: int = 10
    # Duração alvo de cada corte (segundos).
    clip_min_seconds: int = 15
    clip_max_seconds: int = 75
    # Resolução vertical de saída (9:16).
    out_width: int = 1080
    out_height: int = 1920
    # Queimar legendas no vídeo?
    burn_captions: bool = True
    # Palavras por bloco de legenda (estilo viral, punchy).
    caption_words_per_chunk: int = 3

    @property
    def use_gpu(self) -> bool:
        return self.whisper_device == "cuda"


settings = Settings()

# Garante que as pastas existem.
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
