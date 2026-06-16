"""
File utility functions — validation, path management, cleanup.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".ogg", ".m4a"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf"}

MAX_UPLOAD_SIZE_MB = 500


def generate_job_id() -> str:
    """Generate a unique job identifier."""
    return str(uuid.uuid4())


def get_job_dir(job_id: str) -> Path:
    """Get the storage directory for a specific job."""
    settings = get_settings()
    job_dir = settings.storage_dir / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def validate_file_extension(filename: str, allowed: set[str]) -> bool:
    """Check if a file has an allowed extension."""
    ext = Path(filename).suffix.lower()
    return ext in allowed


def validate_video_file(filename: str) -> bool:
    """Validate video file extension."""
    return validate_file_extension(filename, ALLOWED_VIDEO_EXTENSIONS)


def validate_pdf_file(filename: str) -> bool:
    """Validate PDF file extension."""
    return validate_file_extension(filename, ALLOWED_DOCUMENT_EXTENSIONS)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    name = Path(filename).stem
    ext = Path(filename).suffix.lower()
    # Remove non-alphanumeric characters (keep hyphens and underscores)
    name = re.sub(r"[^\w\-]", "_", name)
    return f"{name}{ext}"


def detect_input_type(value: str) -> str:
    """Detect the input type from a URL or file path.

    Returns:
        One of: "instagram_url", "youtube_url", "article_url", "upload", "manual"
    """
    value_lower = value.lower()

    if "instagram.com" in value_lower or "instagr.am" in value_lower:
        return "instagram_url"
    elif "youtube.com" in value_lower or "youtu.be" in value_lower:
        return "youtube_url"
    elif value_lower.startswith(("http://", "https://")):
        return "article_url"
    elif any(value_lower.endswith(ext) for ext in ALLOWED_VIDEO_EXTENSIONS):
        return "upload"
    elif value_lower.endswith(".pdf"):
        return "pdf"
    else:
        return "manual"


def cleanup_job_files(job_id: str) -> None:
    """Remove all temporary files for a job."""
    import shutil
    job_dir = get_job_dir(job_id)
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
        logger.info(f"Cleaned up job files: {job_dir}")
