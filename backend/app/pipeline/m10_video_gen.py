"""
MODULE 10 — Video Generation

Abstraction layer for AI video generation providers (Veo, Kling, Runway).
Generates video clips for scenes that need AI-generated visuals.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.config import get_settings, VideoProvider
from app.providers.video.base import BaseVideoProvider
from app.providers.video.veo import VeoVideoProvider
from app.providers.video.kling import KlingVideoProvider
from app.providers.video.runway import RunwayVideoProvider
from app.providers.video.mock import MockVideoProvider
from app.utils.file_utils import get_job_dir

logger = logging.getLogger(__name__)


def _get_video_provider(provider_name: str) -> BaseVideoProvider:
    """Factory function to get the video provider instance."""
    settings = get_settings()

    if provider_name == "pexels":
        # Find any configured AI video generator
        for p in ["veo", "kling", "runway"]:
            try:
                provider_enum = VideoProvider(p)
                if settings.has_video_provider(provider_enum):
                    provider_name = p
                    logger.info(f"Pexels chosen for AI generation, falling back to configured AI generator: {provider_name}")
                    break
            except ValueError:
                pass
        
        # If still pexels (or nothing found), fall back to mock
        if provider_name == "pexels":
            logger.warning("Pexels selected but AI generation is needed for some scenes, and no AI video provider is configured. Falling back to MockVideoProvider.")
            return MockVideoProvider()

    try:
        provider_enum = VideoProvider(provider_name)
        has_key = settings.has_video_provider(provider_enum)
    except ValueError:
        has_key = False

    if not has_key:
        logger.warning(f"Video provider '{provider_name}' is not configured (missing API key). Falling back to MockVideoProvider.")
        return MockVideoProvider()

    providers = {
        "veo": VeoVideoProvider,
        "kling": KlingVideoProvider,
        "runway": RunwayVideoProvider,
    }

    provider_cls = providers.get(provider_name)
    if not provider_cls:
        raise ValueError(f"Unknown video provider: {provider_name}")

    return provider_cls()


async def generate_scene_videos(
    scene_plan: list[dict[str, Any]],
    job_id: str,
    provider_name: str | None = None,
) -> list[dict[str, Any]]:
    """Generate AI video clips for scenes that don't have stock footage.

    Args:
        scene_plan: Scene plan (possibly with some visual_path already set).
        job_id: Job ID.
        provider_name: Video provider to use.

    Returns:
        Updated scene plan with all visual_path fields populated.
    """
    settings = get_settings()
    provider_name = provider_name or settings.default_video_provider.value

    logger.info(f"[M10] Generating videos: provider={provider_name}")

    # Find scenes that need generation (AI or placeholder fallback)
    pending_scenes = [
        s for s in scene_plan
        if not s.get("visual_path") or s.get("visual_source") in ("ai_pending", "placeholder", "failed")
    ]

    if not pending_scenes:
        logger.info("[M10] All scenes have visuals, skipping AI generation")
        return scene_plan

    provider = _get_video_provider(provider_name)
    job_dir = get_job_dir(job_id)
    visuals_dir = job_dir / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)

    for scene in pending_scenes:
        scene_num = scene.get("scene_number", 0)
        duration = min(scene.get("duration", 5), 10)  # Cap at 10s per clip
        ai_prompt = scene.get("ai_prompt", scene.get("visual_description", ""))

        output_path = visuals_dir / f"scene_{scene_num:02d}_ai.mp4"

        try:
            logger.info(f"[M10] Generating scene {scene_num}: '{ai_prompt[:60]}...'")

            await provider.generate(
                prompt=ai_prompt,
                output_path=output_path,
                duration=duration,
                aspect_ratio="9:16",
            )

            scene["visual_path"] = str(output_path)
            scene["visual_source"] = f"ai_{provider_name}"
            logger.info(f"[M10] Scene {scene_num} generated successfully")

        except Exception as e:
            logger.error(f"[M10] Scene {scene_num} generation failed: {e}")
            scene["visual_path"] = None
            scene["visual_source"] = "failed"

    generated = sum(1 for s in pending_scenes if s.get("visual_path"))
    logger.info(f"[M10] AI videos generated: {generated}/{len(pending_scenes)}")

    return scene_plan
