"""
Integration tests for the reel generation pipeline using mock providers.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
import pytest
from sqlmodel import SQLModel, Session, create_engine

from app.config import get_settings
from app.models.job import Job, JobStatus, InputType
from app.pipeline.orchestrator import run_pipeline


@pytest.fixture(name="session")
def session_fixture():
    import os
    # Setup temporary SQLite database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    db_url = f"sqlite:///{db_path}"

    # Override database settings
    settings = get_settings()
    settings.database_url = db_url

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    # Dispose of engine to close connection pool
    engine.dispose()

    # Close file descriptor to release Windows file lock
    try:
        os.close(fd)
    except OSError:
        pass

    # Cleanup database file
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_full_pipeline_mock_manual(session: Session):
    """Test the end-to-end pipeline using manual job input and mock providers."""
    # Ensure storage paths exist
    settings = get_settings()
    settings.ensure_storage_dirs()

    # Clear API keys to force mock mode for testing
    settings.openai_api_key = ""
    settings.anthropic_api_key = ""
    settings.groq_api_key = ""
    settings.sambanova_api_key = ""
    settings.cerebras_api_key = ""
    settings.elevenlabs_api_key = ""
    settings.cartesia_api_key = ""
    settings.google_api_key = ""
    settings.runwayml_api_secret = ""
    settings.kling_api_key = ""
    settings.pexels_api_key = ""

    # Create a job with manual details
    job = Job(
        input_type=InputType.MANUAL,
        input_value="manual",
        job_data={
            "company_name": "Google",
            "job_role": "Software Engineer",
            "salary": "35 LPA",
            "eligibility": "B.Tech/BE/MS",
            "batch": "2025",
            "experience": "Fresher",
            "location": "Bangalore",
            "last_date": "2026-09-01",
            "apply_link": "https://careers.google.com",
            "important_notes": ["Coding rounds in Python/C++"]
        },
        llm_provider="groq",
        voice_provider="openai",
        video_provider="veo",
        voice_language="hinglish",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    assert job.status == JobStatus.PENDING

    # Run the pipeline
    updated_job = await run_pipeline(job, session)

    # Assertions
    assert updated_job.status in (JobStatus.COMPLETED, JobStatus.COMPLETED_LOW_QUALITY)
    assert updated_job.job_data is not None
    assert updated_job.job_data["company_name"] == "Google"
    assert updated_job.job_data["job_role"] == "Software Engineer"
    assert updated_job.selected_hook is not None
    assert updated_job.script is not None
    assert updated_job.voice_path is not None
    assert updated_job.captions_path is not None
    assert updated_job.output_path is not None
    assert updated_job.overall_score is not None

    assert updated_job.llm_provider == "groq"

    # Check generated file existences
    assert Path(updated_job.voice_path).exists()
    assert Path(updated_job.captions_path).exists()
    assert Path(updated_job.output_path).exists()
