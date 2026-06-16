"""
Mock Video Provider for testing and local development without active API keys.
Generates moving patterns or solid color video clips using FFmpeg.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from app.providers.video.base import BaseVideoProvider, VideoTask, TaskStatus

logger = logging.getLogger(__name__)


class MockVideoProvider(BaseVideoProvider):
    """Mock video provider generating placeholder video clips using FFmpeg."""

    @property
    def provider_name(self) -> str:
        return "Mock Video"

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        resolution: str = "1080x1920",
    ) -> Path:
        logger.info(f"[MockVideo] Generating clip for prompt='{prompt[:50]}...', duration={duration}s")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Parse scene number from output path (e.g., scene_03 -> 3)
        match = re.search(r"scene_(\d+)", output_path.name)
        scene_num = int(match.group(1)) if match else 1

        # Use different colors/effects for different scenes
        colors = ["indigo", "purple", "pink", "teal", "orange", "darkred", "darkblue", "darkgreen"]
        color = colors[scene_num % len(colors)]

        # Generate a video using FFmpeg if available, otherwise write a dummy file
        from app.utils.ffmpeg import check_ffmpeg
        if not check_ffmpeg():
            logger.warning(f"[MockVideo] FFmpeg not found in PATH. Writing a dummy video file instead.")
            output_path.write_bytes(b"dummy_mp4_video_content")
            return output_path

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:s={resolution}:d={duration}:r=30",
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"[MockVideo] FFmpeg clip generation failed: {result.stderr}")
            # Fallback to dummy file
            output_path.write_bytes(b"dummy_mp4_video_content")
            return output_path

        logger.info(f"[MockVideo] Generated clip saved to: {output_path}")
        return output_path

    async def submit_task(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
    ) -> str:
        # Generate a mock task ID
        import uuid
        return f"mock-task-{uuid.uuid4()}"

    async def check_status(self, task_id: str) -> VideoTask:
        return VideoTask(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            provider=self.provider_name,
            output_url="http://localhost:8000/mock/video.mp4",
        )

    async def download(self, task: VideoTask, output_path: Path) -> Path:
        # In async mode, we fall back to generating a file locally
        return await self.generate(
            prompt="Mock async video download",
            output_path=output_path,
            duration=5,
        )
