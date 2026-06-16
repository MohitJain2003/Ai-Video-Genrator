"""
Celery task definitions for the reel generation pipeline.
"""

from __future__ import annotations

import asyncio
import logging

from app.workers.celery_app import celery_app
from app.db.database import get_session
from app.models.job import Job, JobStatus
from app.pipeline.orchestrator import run_pipeline

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@celery_app.task(
    bind=True,
    name="generate_reel",
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=60,
)
def generate_reel_task(self, job_id: str) -> dict:
    """Celery task to run the full reel generation pipeline.

    Args:
        job_id: The job ID to process.

    Returns:
        Dict with job status and output path.
    """
    logger.info(f"[Task] Starting reel generation: job_id={job_id}")

    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if job.status not in (JobStatus.PENDING, JobStatus.FAILED):
            logger.warning(f"[Task] Job {job_id} in unexpected state: {job.status}")

        # Run the async pipeline
        result_job = _run_async(run_pipeline(job, session))

        return {
            "job_id": result_job.id,
            "status": result_job.status.value,
            "output_path": result_job.output_path,
            "overall_score": result_job.overall_score,
            "error": result_job.error_message,
        }

    except Exception as e:
        logger.error(f"[Task] Job {job_id} failed: {e}", exc_info=True)
        # Update job status to failed
        try:
            job = session.get(Job, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                session.add(job)
                session.commit()
        except Exception:
            pass
        raise

    finally:
        session.close()


def run_pipeline_task(job_id: str):
    """Run the pipeline for a job synchronously (designed for FastAPI BackgroundTasks)."""
    logger.info(f"[BackgroundTask] Starting reel generation: job_id={job_id}")
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job:
            logger.error(f"[BackgroundTask] Job not found: {job_id}")
            return

        # Run the async pipeline
        _run_async(run_pipeline(job, session))
        logger.info(f"[BackgroundTask] Job {job_id} completed successfully")
    except Exception as e:
        logger.error(f"[BackgroundTask] Job {job_id} failed: {e}", exc_info=True)
        try:
            job = session.get(Job, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                session.add(job)
                session.commit()
        except Exception as se:
            logger.error(f"[BackgroundTask] Failed to update job status: {se}")
    finally:
        session.close()
