"""
Database models using SQLModel (SQLAlchemy + Pydantic hybrid).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, Text


# ── Enums ────────────────────────────────────────────────────────


class JobStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    TRANSCRIBING = "transcribing"
    EXTRACTING = "extracting"
    GENERATING_HOOKS = "generating_hooks"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_VOICE = "generating_voice"
    PLANNING_SCENES = "planning_scenes"
    GENERATING_CAPTIONS = "generating_captions"
    GENERATING_VISUALS = "generating_visuals"
    GENERATING_VIDEO = "generating_video"
    AWAITING_ASSEMBLY = "awaiting_assembly"
    ASSEMBLING = "assembling"
    QUALITY_CHECK = "quality_check"
    COMPLETED = "completed"
    COMPLETED_LOW_QUALITY = "completed_low_quality"
    FAILED = "failed"


class InputType(str, Enum):
    INSTAGRAM_URL = "instagram_url"
    YOUTUBE_URL = "youtube_url"
    UPLOAD = "upload"
    ARTICLE_URL = "article_url"
    PDF = "pdf"
    MANUAL = "manual"
    ANNOUNCEMENT = "announcement"


# ── Helper ───────────────────────────────────────────────────────


def _generate_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Job Model ────────────────────────────────────────────────────


class Job(SQLModel, table=True):
    """Core job model — tracks a single reel generation pipeline run."""

    __tablename__ = "jobs"

    id: str = Field(default_factory=_generate_uuid, primary_key=True)
    status: JobStatus = Field(default=JobStatus.PENDING, index=True)

    # ── Input ────────────────────────────────────────────────────
    input_type: InputType
    input_value: str = Field(default="", sa_column=Column(Text))  # URL, filename, or "manual"

    # ── Extracted Data ───────────────────────────────────────────
    transcript: Optional[str] = Field(default=None, sa_column=Column(Text))
    job_data: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # ── Generation Outputs ───────────────────────────────────────
    hook_variants: Optional[list[dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    selected_hook: Optional[str] = Field(default=None, sa_column=Column(Text))
    script: Optional[str] = Field(default=None, sa_column=Column(Text))
    scene_plan: Optional[list[dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))

    # ── Quality ──────────────────────────────────────────────────
    quality_scores: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    overall_score: Optional[float] = Field(default=None)

    # ── Provider Selections ──────────────────────────────────────
    llm_provider: Optional[str] = Field(default=None)
    voice_provider: Optional[str] = Field(default=None)
    voice_id: Optional[str] = Field(default=None)
    video_provider: Optional[str] = Field(default=None)
    voice_language: Optional[str] = Field(default=None)

    # ── File Paths ───────────────────────────────────────────────
    upload_path: Optional[str] = Field(default=None)
    audio_path: Optional[str] = Field(default=None)
    voice_path: Optional[str] = Field(default=None)
    captions_path: Optional[str] = Field(default=None)
    output_path: Optional[str] = Field(default=None)

    # ── Error Handling ───────────────────────────────────────────
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    retry_count: int = Field(default=0)

    # ── Timestamps ───────────────────────────────────────────────
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    completed_at: Optional[datetime] = Field(default=None)
