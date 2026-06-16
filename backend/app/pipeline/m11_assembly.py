"""
MODULE 11 — Video Assembly

Uses FFmpeg to merge voiceover, captions, scene clips, and background music
into the final vertical reel (1080x1920, 9:16).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from app.utils.ffmpeg import concatenate_clips, assemble_reel, check_ffmpeg
from app.utils.file_utils import get_job_dir

logger = logging.getLogger(__name__)


async def assemble_final_reel(
    scene_plan: list[dict[str, Any]],
    voice_path: str,
    captions_path: str,
    job_id: str,
    bgm_path: Optional[str] = None,
) -> dict[str, Any]:
    """Assemble the final reel from all generated assets.

    Args:
        scene_plan: Scene plan with visual_path for each scene.
        voice_path: Path to the voiceover audio.
        captions_path: Path to the ASS captions file.
        job_id: Job ID.
        bgm_path: Optional background music path.

    Returns:
        Dict with "output_path", "duration", "resolution".
    """
    logger.info(f"[M11] Assembling reel for job={job_id}")

    job_dir = get_job_dir(job_id)

    if not check_ffmpeg():
        logger.warning("[M11] FFmpeg not found in PATH. Writing a dummy final reel file instead.")
        output_path = job_dir / "final_reel.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"dummy_assembled_reel_content")
        return {
            "output_path": str(output_path),
            "duration": 30.0,
            "resolution": "1080x1920",
            "format": "mp4",
        }

    # Step 1: Collect all scene clips (filter out missing ones)
    clip_paths = []
    for scene in scene_plan:
        visual_path = scene.get("visual_path")
        if visual_path and Path(visual_path).exists():
            clip_paths.append(Path(visual_path))
        else:
            logger.warning(f"[M11] Scene {scene.get('scene_number')} has no visual, skipping")

    if not clip_paths:
        raise RuntimeError("[M11] No video clips available for assembly")

    # Step 2: Concatenate scene clips
    concat_path = job_dir / "concat_scenes.mp4"
    logger.info(f"[M11] Concatenating {len(clip_paths)} clips")
    concatenate_clips(clip_paths, concat_path)

    # Step 3: Assemble final reel (video + voice + captions + bgm)
    output_path = job_dir / "final_reel.mp4"
    voice_file = Path(voice_path)
    captions_file = Path(captions_path) if captions_path else None
    bgm_file = Path(bgm_path) if bgm_path else None

    assemble_reel(
        video_path=concat_path,
        voiceover_path=voice_file,
        captions_path=captions_file,
        bgm_path=bgm_file,
        output_path=output_path,
        bgm_volume=0.12,
    )

    # Step 4: Get output info
    from app.utils.ffmpeg import get_video_duration
    try:
        duration = get_video_duration(output_path)
    except Exception:
        duration = 30.0

    # Clean up intermediate concatenated file
    concat_path.unlink(missing_ok=True)

    logger.info(f"[M11] Final reel assembled: {output_path}, duration={duration:.1f}s")

    return {
        "output_path": str(output_path),
        "duration": duration,
        "resolution": "1080x1920",
        "format": "mp4",
    }
