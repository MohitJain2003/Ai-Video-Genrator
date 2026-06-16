"""
Pexels stock footage provider — free API, no watermarks.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from app.providers.stock.base import BaseStockProvider, StockVideo
from app.config import get_settings

logger = logging.getLogger(__name__)


class PexelsStockProvider(BaseStockProvider):
    """Pexels free stock video API."""

    BASE_URL = "https://api.pexels.com/videos"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.pexels_api_key
        self._headers = {"Authorization": self._api_key}

    @property
    def provider_name(self) -> str:
        return "Pexels"

    async def search(
        self,
        query: str,
        orientation: str = "portrait",
        min_duration: int = 3,
        max_results: int = 5,
    ) -> list[StockVideo]:
        params = {
            "query": query,
            "orientation": orientation,
            "per_page": max_results,
            "size": "medium",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/search",
                params=params,
                headers=self._headers,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for video in data.get("videos", []):
            if video.get("duration", 0) < min_duration:
                continue

            # Find the best quality video file (HD portrait preferred)
            best_file = None
            for vf in video.get("video_files", []):
                if vf.get("height", 0) >= 720:
                    if best_file is None or vf.get("height", 0) > best_file.get("height", 0):
                        best_file = vf

            if not best_file:
                best_file = video.get("video_files", [{}])[0]

            if best_file:
                results.append(
                    StockVideo(
                        id=str(video["id"]),
                        url=video.get("url", ""),
                        download_url=best_file.get("link", ""),
                        width=best_file.get("width", 0),
                        height=best_file.get("height", 0),
                        duration=video.get("duration", 0),
                        source="pexels",
                    )
                )

        logger.info(f"Pexels search '{query}': {len(results)} results")
        return results

    async def download(self, video: StockVideo, output_path: Path) -> Path:
        async with httpx.AsyncClient() as client:
            response = await client.get(video.download_url, timeout=60, follow_redirects=True)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)

        logger.info(f"Pexels video downloaded: {output_path}")
        return output_path
