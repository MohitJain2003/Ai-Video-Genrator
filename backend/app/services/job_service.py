"""
Job service — business logic layer between API and pipeline.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlmodel import Session, select, col

from app.config import get_settings
from app.models.job import Job, JobStatus, InputType
from app.utils.file_utils import get_job_dir, sanitize_filename

logger = logging.getLogger(__name__)


class JobService:
    """Business logic for job management."""

    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()

    def create_job_from_url(
        self,
        url: str,
        input_type: str,
        llm_provider: str | None = None,
        voice_provider: str | None = None,
        voice_id: str | None = None,
        video_provider: str | None = None,
        voice_language: str | None = None,
    ) -> Job:
        """Create a new job from a URL input."""
        job = Job(
            input_type=InputType(input_type),
            input_value=url,
            llm_provider=llm_provider or self.settings.default_llm_provider.value,
            voice_provider=voice_provider or self.settings.default_voice_provider.value,
            voice_id=voice_id,
            video_provider=video_provider or self.settings.default_video_provider.value,
            voice_language=voice_language or self.settings.default_voice_language.value,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        logger.info(f"Created job {job.id} from URL: {url}")
        return job

    def create_job_from_upload(
        self,
        filename: str,
        file_content: bytes,
        input_type: str = "upload",
        llm_provider: str | None = None,
        voice_provider: str | None = None,
        voice_id: str | None = None,
        video_provider: str | None = None,
        voice_language: str | None = None,
    ) -> Job:
        """Create a new job from a file upload."""
        job = Job(
            input_type=InputType(input_type),
            input_value=filename,
            llm_provider=llm_provider or self.settings.default_llm_provider.value,
            voice_provider=voice_provider or self.settings.default_voice_provider.value,
            voice_id=voice_id,
            video_provider=video_provider or self.settings.default_video_provider.value,
            voice_language=voice_language or self.settings.default_voice_language.value,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)

        # Save uploaded file
        safe_name = sanitize_filename(filename)
        job_dir = get_job_dir(job.id)
        upload_path = job_dir / safe_name

        with open(upload_path, "wb") as f:
            f.write(file_content)

        job.upload_path = str(upload_path)
        self.session.add(job)
        self.session.commit()

        logger.info(f"Created job {job.id} from upload: {filename}")
        return job

    def create_job_manual(
        self,
        job_data: dict[str, Any],
        llm_provider: str | None = None,
        voice_provider: str | None = None,
        voice_id: str | None = None,
        video_provider: str | None = None,
        voice_language: str | None = None,
    ) -> Job:
        """Create a new job from manual input."""
        job = Job(
            input_type=InputType.MANUAL,
            input_value="manual",
            job_data=job_data,
            llm_provider=llm_provider or self.settings.default_llm_provider.value,
            voice_provider=voice_provider or self.settings.default_voice_provider.value,
            voice_id=voice_id,
            video_provider=video_provider or self.settings.default_video_provider.value,
            voice_language=voice_language or self.settings.default_voice_language.value,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        logger.info(f"Created job {job.id} from manual input")
        return job

    def create_job_announcement(
        self,
        job_data: dict[str, Any],
    ) -> Job:
        """Create a new job announcement reel job."""
        job = Job(
            input_type=InputType.ANNOUNCEMENT,
            input_value="announcement",
            job_data=job_data,
            llm_provider=self.settings.default_llm_provider.value,
            voice_provider="none",
            video_provider=self.settings.default_video_provider.value,
            voice_language="none",
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        logger.info(f"Created announcement job {job.id}")
        return job

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        return self.session.get(Job, job_id)

    def list_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Job], int]:
        """List jobs with pagination and optional status filter."""
        query = select(Job)

        if status:
            query = query.where(Job.status == status)

        # Count total
        count_query = select(Job)
        if status:
            count_query = count_query.where(Job.status == status)
        total = len(self.session.exec(count_query).all())

        # Apply pagination
        query = query.order_by(col(Job.created_at).desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        jobs = self.session.exec(query).all()
        return list(jobs), total

    def update_job_data(self, job_id: str, updates: dict[str, Any]) -> Job | None:
        """Update extracted job data."""
        job = self.get_job(job_id)
        if not job:
            return None

        current_data = job.job_data or {}
        for key, value in updates.items():
            if value is not None:
                current_data[key] = value

        job.job_data = current_data
        job.updated_at = datetime.now(timezone.utc)
        self.session.add(job)
        self.session.commit()
        return job

    def update_script(self, job_id: str, script: str) -> Job | None:
        """Override the generated script."""
        job = self.get_job(job_id)
        if not job:
            return None

        job.script = script
        job.updated_at = datetime.now(timezone.utc)
        self.session.add(job)
        self.session.commit()
        return job

    def select_hook(self, job_id: str, hook_index: int) -> Job | None:
        """Select a different hook variant."""
        job = self.get_job(job_id)
        if not job or not job.hook_variants:
            return None

        if hook_index < 0 or hook_index >= len(job.hook_variants):
            return None

        # Update selection flags
        for i, hook in enumerate(job.hook_variants):
            hook["is_selected"] = (i == hook_index)

        job.selected_hook = job.hook_variants[hook_index]["text"]
        job.updated_at = datetime.now(timezone.utc)
        self.session.add(job)
        self.session.commit()
        return job

    def delete_job(self, job_id: str) -> bool:
        """Delete a job and its associated files."""
        job = self.get_job(job_id)
        if not job:
            return False

        # Remove files
        job_dir = get_job_dir(job_id)
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)

        self.session.delete(job)
        self.session.commit()
        logger.info(f"Deleted job {job_id}")
        return True
