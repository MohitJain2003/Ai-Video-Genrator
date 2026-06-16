"""
Runway ML video generation provider.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
from runwayml import RunwayML

from app.providers.video.base import BaseVideoProvider, VideoTask, TaskStatus
from app.config import get_settings

logger = logging.getLogger(__name__)


class RunwayVideoProvider(BaseVideoProvider):
    """Runway ML video generation using Gen-4.5."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = RunwayML(api_key=settings.runwayml_api_secret)
        self._model = "gen4.5"

    @property
    def provider_name(self) -> str:
        return "Runway"

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        resolution: str = "1080x1920",
    ) -> Path:
        logger.info(f"Runway generate: prompt='{prompt[:80]}...', duration={duration}")

        # Runway uses text-to-video with model gen4.5
        ratio = "720:1280" if aspect_ratio == "9:16" else "1280:720"

        try:
            task = self._client.text_to_video.create(
                model=self._model,
                prompt_text=prompt,
                ratio=ratio,
                duration=duration,
            ).wait_for_task_output()

            # Download the output
            if task and hasattr(task, "output") and task.output:
                video_url = task.output[0] if isinstance(task.output, list) else task.output
                async with httpx.AsyncClient() as client:
                    response = await client.get(str(video_url), timeout=120)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                logger.info(f"Runway video saved: {output_path}")
                return output_path

            raise RuntimeError("Runway returned no video output")

        except Exception as e:
            logger.error(f"Runway generation failed: {e}")
            raise

    async def submit_task(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
    ) -> str:
        ratio = "720:1280" if aspect_ratio == "9:16" else "1280:720"
        task = self._client.text_to_video.create(
            model=self._model,
            prompt_text=prompt,
            ratio=ratio,
            duration=duration,
        )
        return task.id

    async def check_status(self, task_id: str) -> VideoTask:
        # Runway SDK handles polling internally via wait_for_task_output
        return VideoTask(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            provider=self.provider_name,
        )

    async def download(self, task: VideoTask, output_path: Path) -> Path:
        if not task.output_url:
            raise RuntimeError("No video URL available")

        async with httpx.AsyncClient() as client:
            response = await client.get(task.output_url, timeout=120)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)

        logger.info(f"Runway video saved: {output_path}")
        return output_path
