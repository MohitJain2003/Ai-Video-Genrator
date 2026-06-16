"""
MODULE 9 — Visual Asset Engine

Sources visual assets for each scene — stock footage (Pexels) or AI-generated B-roll.
Ensures 9:16 portrait format, no watermarks, no copyrighted content.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings
from app.providers.stock.pexels import PexelsStockProvider
from app.utils.ffmpeg import scale_video_to_portrait, trim_video
from app.utils.file_utils import get_job_dir

logger = logging.getLogger(__name__)


async def acquire_visuals(
    scene_plan: list[dict[str, Any]],
    job_id: str,
    use_ai_generation: bool = False,
) -> list[dict[str, Any]]:
    """Acquire visual assets for each scene in the plan.

    Args:
        scene_plan: Scene plan from Module 7.
        job_id: Job ID.
        use_ai_generation: If True, use AI video gen instead of stock.

    Returns:
        Updated scene plan with asset paths.
    """
    logger.info(f"[M9] Acquiring visuals: {len(scene_plan)} scenes, ai={use_ai_generation}")

    settings = get_settings()
    job_dir = get_job_dir(job_id)
    visuals_dir = job_dir / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)

    for i, scene in enumerate(scene_plan):
        scene_num = scene.get("scene_number", i + 1)
        duration = scene.get("duration", 5)
        search_query = scene.get("search_query", "corporate office")
        output_path = visuals_dir / f"scene_{scene_num:02d}.mp4"

        try:
            if use_ai_generation:
                # Will be handled by Module 10
                scene["visual_path"] = None
                scene["visual_source"] = "ai_pending"
                logger.info(f"[M9] Scene {scene_num}: marked for AI generation")
            else:
                # Use stock footage
                await _acquire_stock_footage(
                    query=search_query,
                    output_path=output_path,
                    min_duration=duration,
                )
                scene["visual_path"] = str(output_path)
                scene["visual_source"] = "stock"
                logger.info(f"[M9] Scene {scene_num}: stock footage acquired")

        except Exception as e:
            logger.warning(f"[M9] Scene {scene_num} failed: {e}, using placeholder", exc_info=True)
            scene["visual_path"] = None
            scene["visual_source"] = "placeholder"

    acquired = sum(1 for s in scene_plan if s.get("visual_path"))
    logger.info(f"[M9] Visuals acquired: {acquired}/{len(scene_plan)}")
    return scene_plan


async def _acquire_stock_footage(
    query: str,
    output_path: Path,
    min_duration: int = 3,
) -> Path:
    """Search and download stock footage from Pexels."""
    settings = get_settings()

    if not settings.pexels_api_key:
        raise RuntimeError("Pexels API key not configured")

    provider = PexelsStockProvider()

    # Search for portrait videos
    results = await provider.search(
        query=query,
        orientation="portrait",
        min_duration=min_duration,
        max_results=3,
    )

    if not results:
        # Fallback to landscape and crop
        results = await provider.search(
            query=query,
            orientation="landscape",
            min_duration=min_duration,
            max_results=3,
        )

    if not results:
        raise RuntimeError(f"No stock footage found for: {query}")

    # Download the best result
    video = results[0]
    raw_path = output_path.parent / f"raw_{output_path.name}"
    await provider.download(video, raw_path)

    # Scale/crop to portrait 9:16
    scale_video_to_portrait(raw_path, output_path)

    # Clean up raw file
    raw_path.unlink(missing_ok=True)

    # Trim to required duration
    if min_duration and video.duration > min_duration + 2:
        trimmed_path = output_path.parent / f"trimmed_{output_path.name}"
        trim_video(output_path, trimmed_path, start=0, duration=min_duration + 1)
        trimmed_path.replace(output_path)

    return output_path
