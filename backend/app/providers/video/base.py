"""
Abstract base class for AI video generation providers.
All video providers (Veo, Kling, Runway) must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VideoTask:
    """Represents an async video generation task."""
    task_id: str
    status: TaskStatus
    provider: str
    output_url: str = ""
    error: str = ""


class BaseVideoProvider(ABC):
    """Abstract video generation provider interface."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        output_path: Path,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        resolution: str = "1080x1920",
    ) -> Path:
        """Generate a video clip from a text prompt.

        Args:
            prompt: Visual description for the video.
            output_path: Where to save the generated video.
            duration: Duration in seconds.
            aspect_ratio: Aspect ratio string.
            resolution: Resolution string (WxH).

        Returns:
            Path to the generated video file.
        """
        ...

    @abstractmethod
    async def submit_task(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
    ) -> str:
        """Submit an async video generation task.

        Returns:
            Task ID for polling status.
        """
        ...

    @abstractmethod
    async def check_status(self, task_id: str) -> VideoTask:
        """Check the status of an async generation task.

        Returns:
            VideoTask with current status and output URL if completed.
        """
        ...

    @abstractmethod
    async def download(self, task: VideoTask, output_path: Path) -> Path:
        """Download a completed video to local storage.

        Returns:
            Path to the downloaded video file.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...
