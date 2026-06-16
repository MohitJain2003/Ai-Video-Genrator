"""
Kling AI video generation provider.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx

from app.providers.video.base import BaseVideoProvider, VideoTask, TaskStatus
from app.config import get_settings

logger = logging.getLogger(__name__)


class KlingVideoProvider(BaseVideoProvider):
    """Kling AI video generation via REST API."""

    BASE_URL = "https://api.klingai.com/v1"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.kling_api_key
        self._model = "kling-3.0"
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    @property
    def provider_name(self) -> str:
        return "Kling"

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        resolution: str = "1080x1920",
    ) -> Path:
        task_id = await self.submit_task(prompt, duration, aspect_ratio)

        # Poll for completion
        max_wait = 300
        elapsed = 0
        while elapsed < max_wait:
            task = await self.check_status(task_id)
            if task.status == TaskStatus.COMPLETED:
                return await self.download(task, output_path)
            elif task.status == TaskStatus.FAILED:
                raise RuntimeError(f"Kling generation failed: {task.error}")
            time.sleep(10)
            elapsed += 10

        raise TimeoutError(f"Kling generation timed out after {max_wait}s")

    async def submit_task(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
    ) -> str:
        payload = {
            "model": self._model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/videos/generations",
                json=payload,
                headers=self._headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            task_id = data.get("task_id", data.get("data", {}).get("task_id", ""))
            logger.info(f"Kling task submitted: {task_id}")
            return task_id

    async def check_status(self, task_id: str) -> VideoTask:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/tasks/{task_id}",
                headers=self._headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

        status_str = data.get("status", data.get("data", {}).get("status", "processing"))
        status_map = {
            "completed": TaskStatus.COMPLETED,
            "succeed": TaskStatus.COMPLETED,
            "failed": TaskStatus.FAILED,
            "processing": TaskStatus.PROCESSING,
            "pending": TaskStatus.PENDING,
        }

        output_url = ""
        if "output" in data:
            output_url = data["output"].get("video_url", "")
        elif "data" in data and "output" in data["data"]:
            output_url = data["data"]["output"].get("video_url", "")

        return VideoTask(
            task_id=task_id,
            status=status_map.get(status_str, TaskStatus.PROCESSING),
            provider=self.provider_name,
            output_url=output_url,
            error=data.get("error", ""),
        )

    async def download(self, task: VideoTask, output_path: Path) -> Path:
        if not task.output_url:
            raise RuntimeError("No video URL available for download")

        async with httpx.AsyncClient() as client:
            response = await client.get(task.output_url, timeout=120)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)

        logger.info(f"Kling video saved: {output_path}")
        return output_path
