"""Modelos de dados (Pydantic) usados pela API e pelo pipeline."""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    downloading = "downloading"
    transcribing = "transcribing"
    analyzing = "analyzing"
    rendering = "rendering"
    done = "done"
    error = "error"


class Word(BaseModel):
    start: float
    end: float
    text: str


class Segment(BaseModel):
    start: float
    end: float
    text: str
    words: list[Word] = Field(default_factory=list)


class ClipPlan(BaseModel):
    """Um corte escolhido pela IA (antes de renderizar)."""
    start: float
    end: float
    title: str
    hook: str = ""
    theme: str = ""
    virality_score: int = 0  # 0..100
    reason: str = ""


class Clip(ClipPlan):
    """Um corte já renderizado, pronto para download."""
    id: str
    filename: str
    url: str
    duration: float


class JobCreate(BaseModel):
    youtube_url: Optional[str] = None
    language: Optional[str] = None
    max_clips: Optional[int] = None


class Job(BaseModel):
    id: str
    status: JobStatus = JobStatus.queued
    source: str = ""             # "upload" ou URL
    progress: int = 0            # 0..100
    message: str = ""
    error: str = ""
    transcript_preview: str = ""
    clips: list[Clip] = Field(default_factory=list)
