"""
Abstract base class for stock footage providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StockVideo:
    """Metadata about a stock video clip."""
    id: str
    url: str
    download_url: str
    width: int
    height: int
    duration: float
    source: str


class BaseStockProvider(ABC):
    """Abstract stock footage provider interface."""

    @abstractmethod
    async def search(
        self,
        query: str,
        orientation: str = "portrait",
        min_duration: int = 3,
        max_results: int = 5,
    ) -> list[StockVideo]:
        """Search for stock video clips.

        Args:
            query: Search query describing the desired footage.
            orientation: "portrait", "landscape", or "square".
            min_duration: Minimum clip duration in seconds.
            max_results: Maximum number of results.

        Returns:
            List of matching stock videos.
        """
        ...

    @abstractmethod
    async def download(self, video: StockVideo, output_path: Path) -> Path:
        """Download a stock video to local storage.

        Returns:
            Path to the downloaded video file.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
