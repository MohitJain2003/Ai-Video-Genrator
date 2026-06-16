"""
MODULE 1 — Video Ingestion

Accepts: mp4, mov, webm, Instagram URLs, YouTube URLs, article URLs, PDFs.
Extracts: audio, keyframes, metadata.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional

import httpx
import yt_dlp
import pdfplumber
from bs4 import BeautifulSoup

from app.utils.ffmpeg import extract_audio, extract_keyframes, get_video_duration
from app.utils.file_utils import get_job_dir

logger = logging.getLogger(__name__)


class IngestionResult:
    """Output of the ingestion module."""

    def __init__(
        self,
        audio_path: Optional[Path] = None,
        frames: Optional[list[Path]] = None,
        text_content: Optional[str] = None,
        metadata: Optional[dict] = None,
        skip_transcription: bool = False,
    ):
        self.audio_path = audio_path
        self.frames = frames or []
        self.text_content = text_content
        self.metadata = metadata or {}
        self.skip_transcription = skip_transcription


async def ingest(
    job_id: str,
    input_type: str,
    input_value: str,
    upload_path: Optional[str] = None,
) -> IngestionResult:
    """Main ingestion dispatcher — routes to the correct handler.

    Args:
        job_id: Unique job identifier.
        input_type: One of: instagram_url, youtube_url, upload, article_url, pdf, manual.
        input_value: URL, file path, or "manual".
        upload_path: Path to uploaded file (for upload/pdf types).

    Returns:
        IngestionResult with extracted data.
    """
    logger.info(f"[M1] Ingesting job={job_id}, type={input_type}")

    if input_type in ("instagram_url", "youtube_url"):
        return await _ingest_from_url(job_id, input_value)
    elif input_type == "upload":
        return await _ingest_from_file(job_id, Path(upload_path or input_value))
    elif input_type == "article_url":
        return await _ingest_from_article(job_id, input_value)
    elif input_type == "pdf":
        return await _ingest_from_pdf(job_id, Path(upload_path or input_value))
    elif input_type == "manual":
        return IngestionResult(skip_transcription=True)
    else:
        raise ValueError(f"Unknown input type: {input_type}")


async def _ingest_from_url(job_id: str, url: str) -> IngestionResult:
    """Download video from Instagram/YouTube and extract audio + frames."""
    job_dir = get_job_dir(job_id)
    video_path = job_dir / "source_video.mp4"

    # Download using yt-dlp
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(video_path),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    logger.info(f"[M1] Downloading from URL: {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    metadata = {
        "title": info.get("title", ""),
        "duration": info.get("duration", 0),
        "uploader": info.get("uploader", ""),
        "source_url": url,
    }

    # Check if the video file exists (yt-dlp may append extension)
    if not video_path.exists():
        # Try common variations
        for ext in [".mp4", ".webm", ".mkv"]:
            alt = job_dir / f"source_video{ext}"
            if alt.exists():
                video_path = alt
                break

    if not video_path.exists():
        raise FileNotFoundError(f"Downloaded video not found at {video_path}")

    # Extract audio for transcription
    audio_path = job_dir / "audio.wav"
    extract_audio(video_path, audio_path)

    # Extract keyframes for visual reference
    frames_dir = job_dir / "frames"
    frames = extract_keyframes(video_path, frames_dir, fps=0.5)

    duration = get_video_duration(video_path)
    metadata["duration"] = duration

    logger.info(f"[M1] Ingested from URL: audio={audio_path.exists()}, frames={len(frames)}")
    return IngestionResult(
        audio_path=audio_path,
        frames=frames,
        metadata=metadata,
    )


async def _ingest_from_file(job_id: str, file_path: Path) -> IngestionResult:
    """Process an uploaded video file."""
    job_dir = get_job_dir(job_id)

    if not file_path.exists():
        raise FileNotFoundError(f"Uploaded file not found: {file_path}")

    # Extract audio
    audio_path = job_dir / "audio.wav"
    extract_audio(file_path, audio_path)

    # Extract keyframes
    frames_dir = job_dir / "frames"
    frames = extract_keyframes(file_path, frames_dir, fps=0.5)

    duration = get_video_duration(file_path)
    metadata = {
        "source_file": file_path.name,
        "duration": duration,
    }

    logger.info(f"[M1] Ingested from file: audio={audio_path.exists()}, frames={len(frames)}")
    return IngestionResult(
        audio_path=audio_path,
        frames=frames,
        metadata=metadata,
    )


async def _ingest_from_article(job_id: str, url: str) -> IngestionResult:
    """Fetch and parse an article/job posting URL."""
    logger.info(f"[M1] Fetching article: {url}")

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=15, follow_redirects=True)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()

    # Extract text content
    text = soup.get_text(separator="\n", strip=True)

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text_content = "\n".join(lines)

    metadata = {
        "source_url": url,
        "title": soup.title.string if soup.title else "",
    }

    logger.info(f"[M1] Article extracted: {len(text_content)} chars")
    return IngestionResult(
        text_content=text_content,
        metadata=metadata,
        skip_transcription=True,
    )


async def _ingest_from_pdf(job_id: str, pdf_path: Path) -> IngestionResult:
    """Extract text from a PDF file."""
    logger.info(f"[M1] Parsing PDF: {pdf_path}")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    text_parts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    text_content = "\n\n".join(text_parts)

    metadata = {
        "source_file": pdf_path.name,
        "pages": len(text_parts),
    }

    logger.info(f"[M1] PDF extracted: {len(text_content)} chars, {len(text_parts)} pages")
    return IngestionResult(
        text_content=text_content,
        metadata=metadata,
        skip_transcription=True,
    )
