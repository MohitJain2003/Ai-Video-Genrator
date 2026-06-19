"""
REST API routes for the reel generation system.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.config import get_settings, LLMProvider, VoiceProvider, VideoProvider
from app.db.database import get_session, get_session_dep
from app.models.schemas import (
    CreateJobFromURL,
    CreateJobManual,
    CreateJobAnnouncement,
    UpdateJobData,
    UpdateScript,
    SelectHook,
    JobResponse,
    JobListResponse,
    HookVariant,
    QualityScoreResponse,
    ProvidersResponse,
    ProviderStatus,
    HealthResponse,
    ErrorResponse,
)
from app.services.job_service import JobService
from app.utils.file_utils import detect_input_type, validate_video_file, validate_pdf_file
from app.workers.tasks import generate_reel_task, run_pipeline_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["jobs"])


def _get_service(session: Session = Depends(get_session_dep)) -> JobService:
    return JobService(session)


def queue_job_task(job_id: str, background_tasks: BackgroundTasks):
    """Queue a job using Celery or FastAPI BackgroundTasks depending on eager mode."""
    from app.workers.celery_app import celery_app
    if not celery_app.conf.task_always_eager:
        generate_reel_task.delay(job_id)
        logger.info(f"Queued job {job_id} using Celery")
    else:
        background_tasks.add_task(run_pipeline_task, job_id)
        logger.info(f"Queued job {job_id} using FastAPI BackgroundTasks (Celery eager fallback)")


# ── Health & Info ────────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    redis_ok = False
    try:
        import redis
        settings = get_settings()
        r = redis.from_url(settings.redis_url)
        r.ping()
        redis_ok = True
    except Exception:
        pass

    return HealthResponse(status="healthy", redis=redis_ok)


@router.get("/providers", response_model=ProvidersResponse)
async def list_providers():
    """List available AI providers and their status."""
    settings = get_settings()
    providers = []

    for p in LLMProvider:
        providers.append(ProviderStatus(
            name=p.value, type="llm", available=settings.has_llm_provider(p)
        ))
    for p in VoiceProvider:
        providers.append(ProviderStatus(
            name=p.value, type="voice", available=settings.has_voice_provider(p)
        ))
    for p in VideoProvider:
        providers.append(ProviderStatus(
            name=p.value, type="video", available=settings.has_video_provider(p)
        ))

    # Pexels
    providers.append(ProviderStatus(
        name="pexels", type="stock", available=bool(settings.pexels_api_key)
    ))

    return ProvidersResponse(providers=providers)


@router.get("/voices")
async def list_voices(
    provider: str = Query("elevenlabs"),
    language: str = Query("en"),
):
    """List available voices for a voice provider."""
    try:
        from app.pipeline.m06_voice import _get_voice_provider
        voice_provider = _get_voice_provider(provider)
        voices = await voice_provider.list_voices(language=language)
        return {"voices": [
            {"id": v.id, "name": v.name, "gender": v.gender, "language": v.language}
            for v in voices
        ]}
    except Exception as e:
        logger.exception("Failed to list voices")
        raise HTTPException(500, f"Failed to list voices: {str(e)}")


# ── Job CRUD ─────────────────────────────────────────────────────


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job_from_url(
    data: CreateJobFromURL,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(_get_service),
):
    """Create a new job from a URL (Instagram, YouTube, article)."""
    input_type = detect_input_type(data.url)

    if input_type == "manual":
        raise HTTPException(400, "Invalid URL. Use POST /jobs/manual for manual input.")

    job = service.create_job_from_url(
        url=data.url,
        input_type=input_type,
        llm_provider=data.llm_provider,
        voice_provider=data.voice_provider,
        voice_id=data.voice_id,
        video_provider=data.video_provider,
        voice_language=data.voice_language,
    )

    # Queue the pipeline
    queue_job_task(job.id, background_tasks)
    logger.info(f"Job {job.id} queued for processing")

    return JobResponse.model_validate(job)


@router.post("/jobs/upload", response_model=JobResponse, status_code=201)
async def create_job_from_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    llm_provider: str | None = Form(None),
    voice_provider: str | None = Form(None),
    voice_id: str | None = Form(None),
    video_provider: str | None = Form(None),
    voice_language: str | None = Form(None),
    service: JobService = Depends(_get_service),
):
    """Create a new job from a file upload (video or PDF)."""
    filename = file.filename or "upload"

    # Determine input type
    if validate_video_file(filename):
        input_type = "upload"
    elif validate_pdf_file(filename):
        input_type = "pdf"
    else:
        raise HTTPException(400, f"Unsupported file type: {filename}. Supported: mp4, mov, webm, pdf")

    content = await file.read()
    if len(content) > 500 * 1024 * 1024:  # 500MB limit
        raise HTTPException(413, "File too large. Maximum 500MB.")

    job = service.create_job_from_upload(
        filename=filename,
        file_content=content,
        input_type=input_type,
        llm_provider=llm_provider,
        voice_provider=voice_provider,
        voice_id=voice_id,
        video_provider=video_provider,
        voice_language=voice_language,
    )

    # Queue the pipeline
    queue_job_task(job.id, background_tasks)
    logger.info(f"Job {job.id} (upload) queued for processing")

    return JobResponse.model_validate(job)


@router.post("/jobs/manual", response_model=JobResponse, status_code=201)
async def create_job_manual(
    data: CreateJobManual,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(_get_service),
):
    """Create a new job from manual job data input."""
    job = service.create_job_manual(
        job_data=data.job_data.model_dump(),
        llm_provider=data.llm_provider,
        voice_provider=data.voice_provider,
        voice_id=data.voice_id,
        video_provider=data.video_provider,
        voice_language=data.voice_language,
    )

    # Queue the pipeline
    queue_job_task(job.id, background_tasks)
    logger.info(f"Job {job.id} (manual) queued for processing")

    return JobResponse.model_validate(job)


@router.post("/jobs/announcement", response_model=JobResponse, status_code=201)
async def create_job_announcement(
    data: CreateJobAnnouncement,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(_get_service),
):
    """Create a new job announcement reel job."""
    job = service.create_job_announcement(
        job_data=data.job_data.model_dump(),
    )

    # Queue the pipeline
    queue_job_task(job.id, background_tasks)
    logger.info(f"Job {job.id} (announcement) queued for processing")

    return JobResponse.model_validate(job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    service: JobService = Depends(_get_service),
):
    """List all jobs with pagination and optional status filter."""
    jobs, total = service.list_jobs(page=page, page_size=page_size, status=status)
    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    service: JobService = Depends(_get_service),
):
    """Get job details by ID."""
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return JobResponse.model_validate(job)


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    service: JobService = Depends(_get_service),
):
    """Delete a job and all associated files."""
    if not service.delete_job(job_id):
        raise HTTPException(404, f"Job not found: {job_id}")
    return {"message": f"Job {job_id} deleted"}


@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    service: JobService = Depends(_get_service),
):
    """Retry a failed job."""
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")

    if job.status.value not in ("failed", "completed_low_quality"):
        raise HTTPException(400, f"Job is in state '{job.status.value}', cannot retry.")

    from app.models.job import JobStatus
    job.status = JobStatus.PENDING
    job.error_message = None
    service.session.add(job)
    service.session.commit()

    queue_job_task(job.id, background_tasks)
    return JobResponse.model_validate(job)


# ── Job Details ──────────────────────────────────────────────────


@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: str,
    service: JobService = Depends(_get_service),
):
    """Get real-time processing status."""
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return {
        "job_id": job.id,
        "status": job.status.value,
        "overall_score": job.overall_score,
        "retry_count": job.retry_count,
        "error_message": job.error_message,
    }


@router.get("/jobs/{job_id}/script")
async def get_script(
    job_id: str,
    service: JobService = Depends(_get_service),
):
    """Get the generated script."""
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return {"script": job.script, "selected_hook": job.selected_hook}


@router.put("/jobs/{job_id}/script", response_model=JobResponse)
async def update_script(
    job_id: str,
    data: UpdateScript,
    service: JobService = Depends(_get_service),
):
    """Edit/override the generated script."""
    job = service.update_script(job_id, data.script)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return JobResponse.model_validate(job)


@router.get("/jobs/{job_id}/hooks")
async def get_hooks(
    job_id: str,
    service: JobService = Depends(_get_service),
):
    """Get all hook variants with scores."""
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return {
        "hooks": job.hook_variants or [],
        "selected_hook": job.selected_hook,
    }


@router.put("/jobs/{job_id}/hooks/select", response_model=JobResponse)
async def select_hook(
    job_id: str,
    data: SelectHook,
    service: JobService = Depends(_get_service),
):
    """Override the auto-selected hook."""
    job = service.select_hook(job_id, data.hook_index)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return JobResponse.model_validate(job)


@router.get("/jobs/{job_id}/job-data")
async def get_job_data(
    job_id: str,
    service: JobService = Depends(_get_service),
):
    """Get extracted job information JSON."""
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return {"job_data": job.job_data}


@router.put("/jobs/{job_id}/job-data", response_model=JobResponse)
async def update_job_data(
    job_id: str,
    data: UpdateJobData,
    service: JobService = Depends(_get_service),
):
    """Edit extracted job data before generation."""
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    job = service.update_job_data(job_id, updates)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return JobResponse.model_validate(job)


@router.get("/jobs/{job_id}/download")
async def download_reel(
    job_id: str,
    service: JobService = Depends(_get_service),
):
    """Download the final reel MP4."""
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")

    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(404, "Final reel not available yet")

    return FileResponse(
        path=job.output_path,
        media_type="video/mp4",
        filename=f"reel_{job_id[:8]}.mp4",
    )


@router.get("/jobs/{job_id}/preview")
async def preview_reel(
    job_id: str,
    service: JobService = Depends(_get_service),
):
    """Stream reel preview."""
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")

    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(404, "Reel not available for preview")

    return FileResponse(
        path=job.output_path,
        media_type="video/mp4",
    )


# ── Extract Only ─────────────────────────────────────────────────


@router.post("/extract")
async def extract_only(
    data: CreateJobFromURL,
    service: JobService = Depends(_get_service),
):
    """Extract job info only (no reel generation)."""
    # This creates a job but only runs M1-M3
    input_type = detect_input_type(data.url)
    job = service.create_job_from_url(
        url=data.url,
        input_type=input_type,
    )
    # TODO: Create a separate extract-only Celery task
    return {"job_id": job.id, "message": "Extraction job queued"}
