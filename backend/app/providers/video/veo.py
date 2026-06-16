"""
Google Veo video generation provider.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx
from google import genai
from google.genai import types

from app.providers.video.base import BaseVideoProvider, VideoTask, TaskStatus
from app.config import get_settings

logger = logging.getLogger(__name__)


class VeoVideoProvider(BaseVideoProvider):
    """Google Veo video generation via Gemini API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.google_api_key)
        self._model = "veo-3.1-fast-generate-preview"

    @property
    def provider_name(self) -> str:
        return "Google Veo"

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        resolution: str = "1080x1920",
    ) -> Path:
        logger.info(f"Veo generate: prompt='{prompt[:80]}...', duration={duration}")

        operation = self._client.models.generate_videos(
            model=self._model,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                resolution="720p",
            ),
        )

        # Poll until done
        max_wait = 300  # 5 minutes
        elapsed = 0
        while not operation.done and elapsed < max_wait:
            time.sleep(10)
            elapsed += 10
            operation = self._client.operations.get(operation)
            logger.info(f"Veo polling: {elapsed}s elapsed")

        if not operation.done:
            raise TimeoutError(f"Veo generation timed out after {max_wait}s")

        if not operation.response or not operation.response.generated_videos:
            raise RuntimeError("Veo returned no video output")

        # Download the video
        generated = operation.response.generated_videos[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.files.download(file=generated.video)
        generated.video.save(str(output_path))

        logger.info(f"Veo video saved: {output_path}")
        return output_path

    async def submit_task(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
    ) -> str:
        operation = self._client.models.generate_videos(
            model=self._model,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                resolution="720p",
            ),
        )
        return operation.name or str(id(operation))

    async def check_status(self, task_id: str) -> VideoTask:
        # Veo uses operation-based polling — simplified here
        return VideoTask(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            provider=self.provider_name,
        )

    async def download(self, task: VideoTask, output_path: Path) -> Path:
        if task.output_url:
            async with httpx.AsyncClient() as client:
                response = await client.get(task.output_url)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
        return output_path
