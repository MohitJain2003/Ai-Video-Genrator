"""
Pydantic schemas for API request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


# ── Request Schemas ──────────────────────────────────────────────


class ManualJobInput(BaseModel):
    """Manual job data entry."""
    company_name: str = Field(..., min_length=1, max_length=200)
    job_role: str = Field(..., min_length=1, max_length=200)
    salary: Optional[str] = None
    eligibility: Optional[str] = None
    degree_requirements: Optional[list[str]] = None
    batch: Optional[str] = None
    experience: Optional[str] = None
    location: Optional[str] = None
    last_date: Optional[str] = None
    selection_process: Optional[list[str]] = None
    apply_link: Optional[str] = None
    important_notes: Optional[list[str]] = None


class CreateJobFromURL(BaseModel):
    """Create job from a URL (Instagram, YouTube, or article)."""
    url: str = Field(..., min_length=5)
    llm_provider: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_id: Optional[str] = None
    video_provider: Optional[str] = None
    voice_language: Optional[str] = None


class CreateJobManual(BaseModel):
    """Create job from manual input."""
    job_data: ManualJobInput
    llm_provider: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_id: Optional[str] = None
    video_provider: Optional[str] = None
    voice_language: Optional[str] = None


class AnnouncementJobInput(BaseModel):
    """Job Announcement input fields."""
    company_name: str = Field(..., min_length=1, max_length=200)
    job_role: str = Field(..., min_length=1, max_length=200)
    salary: Optional[str] = None
    eligibility: Optional[str] = None
    batch: Optional[str] = None
    experience: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None
    last_date: Optional[str] = None
    cta_text: Optional[str] = None
    bgm_name: Optional[str] = None


class CreateJobAnnouncement(BaseModel):
    """Request schema for creating a job announcement reel."""
    job_data: AnnouncementJobInput


class UpdateJobData(BaseModel):
    """Edit extracted job data before generation."""
    company_name: Optional[str] = None
    job_role: Optional[str] = None
    salary: Optional[str] = None
    eligibility: Optional[str] = None
    degree_requirements: Optional[list[str]] = None
    batch: Optional[str] = None
    experience: Optional[str] = None
    location: Optional[str] = None
    last_date: Optional[str] = None
    selection_process: Optional[list[str]] = None
    apply_link: Optional[str] = None
    important_notes: Optional[list[str]] = None


class UpdateScript(BaseModel):
    """Override generated script."""
    script: str = Field(..., min_length=10)


class SelectHook(BaseModel):
    """Override auto-selected hook."""
    hook_index: int = Field(..., ge=0, le=9)


# ── Response Schemas ─────────────────────────────────────────────


class JobDataResponse(BaseModel):
    """Extracted job information."""
    company_name: Optional[str] = None
    job_role: Optional[str] = None
    salary: Optional[str] = None
    eligibility: Optional[str] = None
    degree_requirements: Optional[list[str]] = None
    batch: Optional[str] = None
    experience: Optional[str] = None
    location: Optional[str] = None
    last_date: Optional[str] = None
    selection_process: Optional[list[str]] = None
    apply_link: Optional[str] = None
    important_notes: Optional[list[str]] = None


class HookVariant(BaseModel):
    """Single hook variant with score."""
    index: int
    text: str
    score: float
    is_selected: bool = False


class QualityScoreResponse(BaseModel):
    """Quality scoring breakdown."""
    hook_quality: float = 0
    retention_score: float = 0
    readability: float = 0
    cta_effectiveness: float = 0
    overall_score: float = 0


class JobResponse(BaseModel):
    """Full job response."""
    id: str
    status: str
    input_type: str
    input_value: str
    job_data: Optional[dict[str, Any]] = None
    hook_variants: Optional[list[dict[str, Any]]] = None
    selected_hook: Optional[str] = None
    script: Optional[str] = None
    scene_plan: Optional[list[dict[str, Any]]] = None
    quality_scores: Optional[dict[str, Any]] = None
    overall_score: Optional[float] = None
    llm_provider: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_id: Optional[str] = None
    video_provider: Optional[str] = None
    voice_language: Optional[str] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Paginated job list."""
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


class ProviderStatus(BaseModel):
    """Status of a single provider."""
    name: str
    type: str  # "llm", "voice", "video"
    available: bool


class ProvidersResponse(BaseModel):
    """All available providers."""
    providers: list[ProviderStatus]


class HealthResponse(BaseModel):
    """Health check."""
    status: str = "healthy"
    version: str = "1.0.0"
    redis: bool = False


class StatusUpdate(BaseModel):
    """WebSocket status update."""
    job_id: str
    status: str
    progress: Optional[float] = None  # 0.0 - 1.0
    message: Optional[str] = None
    timestamp: datetime


class ErrorResponse(BaseModel):
    """API error response."""
    error: str
    detail: Optional[str] = None
