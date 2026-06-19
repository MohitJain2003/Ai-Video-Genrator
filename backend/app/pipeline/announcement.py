"""
Job Announcement Reel Generation Pipeline.
Generates vertical (9:16) video with random office background footage and ASS overlay cards.
"""

from __future__ import annotations

import logging
import random
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import httpx

from app.config import get_settings
from app.models.job import Job, JobStatus
from app.providers.stock.pexels import PexelsStockProvider
from app.providers.video.mock import MockVideoProvider
from app.utils.ffmpeg import concatenate_clips, check_ffmpeg, scale_video_to_portrait, trim_video
from app.utils.file_utils import get_job_dir

logger = logging.getLogger(__name__)

OFFICE_QUERIES = [
    "modern office interior",
    "employee working laptop",
    "office coding screen",
    "corporate workspace collaboration",
    "business meeting conference room",
    "office tour desk setup",
    "keyboard typing technology",
    "office glass cabin",
    "team meeting presentation"
]

BGM_URLS = {
    "chill_lofi": "https://assets.mixkit.co/music/preview/mixkit-lo-fi-dreams-1320.mp3",
    "tech_vibes": "https://assets.mixkit.co/music/preview/mixkit-tech-house-vibes-130.mp3",
    "lively_lofi": "https://assets.mixkit.co/music/preview/mixkit-lively-lo-fi-1317.mp3",
}


async def run_announcement_pipeline(
    job: Job,
    session: Any,
    on_status: Optional[callable] = None,
) -> Job:
    """Run the job announcement reel generation pipeline.

    Args:
        job: The Job model instance.
        session: Database session.
        on_status: Status callback.

    Returns:
        Updated Job instance.
    """
    settings = get_settings()

    def _update_status(status: JobStatus, message: str = ""):
        job.status = status
        job.updated_at = datetime_now()
        session.add(job)
        session.commit()
        logger.info(f"[Announcement Pipeline] Job {job.id}: {status.value} — {message}")
        if on_status:
            on_status(job.id, status.value, message)

    try:
        # 1. Start Ingestion
        _update_status(JobStatus.INGESTING, "Initializing announcement pipeline...")
        job_dir = get_job_dir(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)

        job_data = job.job_data or {}
        company = job_data.get("company_name", "Company")
        role = job_data.get("job_role", "Position")

        # 2. Source Visual Assets
        _update_status(JobStatus.GENERATING_VISUALS, "Downloading random office background clips...")
        
        # Select 4 random queries
        queries = random.sample(OFFICE_QUERIES, k=min(4, len(OFFICE_QUERIES)))
        clip_paths = []
        visuals_dir = job_dir / "visuals"
        visuals_dir.mkdir(parents=True, exist_ok=True)

        has_pexels = bool(settings.pexels_api_key)
        provider = PexelsStockProvider() if has_pexels else None

        for idx, query in enumerate(queries):
            output_path = visuals_dir / f"scene_{idx+1:02d}.mp4"
            clip_downloaded = False

            if has_pexels and provider:
                try:
                    logger.info(f"Searching Pexels for query: '{query}'")
                    results = await provider.search(query=query, orientation="portrait", min_duration=5, max_results=3)
                    if not results:
                        results = await provider.search(query=query, orientation="landscape", min_duration=5, max_results=3)
                    
                    if results:
                        raw_path = visuals_dir / f"raw_{idx+1:02d}.mp4"
                        await provider.download(results[0], raw_path)
                        # Crop to portrait and trim to 5s
                        scale_video_to_portrait(raw_path, output_path)
                        raw_path.unlink(missing_ok=True)
                        
                        trimmed_path = visuals_dir / f"trimmed_{idx+1:02d}.mp4"
                        trim_video(output_path, trimmed_path, start=0, duration=5.0)
                        trimmed_path.replace(output_path)
                        
                        clip_paths.append(output_path)
                        clip_downloaded = True
                        logger.info(f"Successfully downloaded B-roll clip {idx+1}")
                except Exception as e:
                    logger.warning(f"Failed to download Pexels clip for '{query}': {e}. Falling back to mock clip.")

            if not clip_downloaded:
                # Mock clip fallback
                mock_provider = MockVideoProvider()
                await mock_provider.generate(
                    prompt=f"Office scene: {query}",
                    output_path=output_path,
                    duration=5,
                )
                clip_paths.append(output_path)

        # Concatenate background clips
        _update_status(JobStatus.GENERATING_VISUALS, "Merging background clips...")
        concat_bg_path = job_dir / "concat_bg.mp4"
        concatenate_clips(clip_paths, concat_bg_path)

        # 3. Apply Dark Translucent Overlay via FFmpeg
        _update_status(JobStatus.ASSEMBLING, "Applying dark translucent overlay and compiling layouts...")
        overlay_bg_path = job_dir / "overlay_bg.mp4"
        
        if check_ffmpeg():
            # Add a dark translucent overlay (black with 45% opacity)
            cmd = [
                "ffmpeg", "-y",
                "-i", str(concat_bg_path),
                "-vf", "drawbox=y=0:color=black@0.45:width=iw:height=ih:t=fill",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                str(overlay_bg_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to apply dark overlay: {result.stderr}")
                concat_bg_path.replace(overlay_bg_path)
        else:
            concat_bg_path.replace(overlay_bg_path)

        # 4. Generate ASS Subtitles file
        ass_path = job_dir / "announcement.ass"
        generate_announcement_ass(job_data, ass_path, duration=20.0)
        job.captions_path = str(ass_path)

        # 5. Acquire Background Music (BGM)
        bgm_name = job_data.get("bgm_name", "chill_lofi")
        bgm_path = None
        
        if bgm_name in BGM_URLS:
            bgm_dir = Path("backend/storage/bgm")
            bgm_dir.mkdir(parents=True, exist_ok=True)
            cached_bgm_path = bgm_dir / f"{bgm_name}.mp3"
            
            if not cached_bgm_path.exists():
                try:
                    logger.info(f"Downloading BGM track: {bgm_name}")
                    async with httpx.AsyncClient() as client:
                        response = await client.get(BGM_URLS[bgm_name], timeout=30)
                        response.raise_for_status()
                        cached_bgm_path.write_bytes(response.content)
                    logger.info("BGM downloaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to download BGM '{bgm_name}': {e}. Video will render with silent audio.")
            
            if cached_bgm_path.exists():
                bgm_path = cached_bgm_path

        # 6. Assembly using FFmpeg
        final_output_path = job_dir / "final_reel.mp4"
        
        if check_ffmpeg():
            # Build filters
            vf_filters = []
            
            # Burn in ASS subtitle file
            ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
            vf_filters.append(f"ass={ass_filter_path}")
            
            # Force 1080x1920 9:16
            vf_filters.append("scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2")
            
            inputs = ["-i", str(overlay_bg_path)]
            
            if bgm_path and bgm_path.exists():
                inputs.extend(["-i", str(bgm_path)])
                # Mix BGM at 18% volume, trim to match video length
                audio_filters = "-filter_complex [1:a]volume=0.18[bgm];[bgm]atrim=duration=20.0[aout]"
                audio_map = ["-map", "[aout]"]
            else:
                # Silent track generator
                inputs.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
                audio_filters = ""
                audio_map = ["-map", "1:a"]

            cmd = [
                "ffmpeg", "-y",
                *inputs
            ]
            
            if audio_filters:
                cmd.extend(audio_filters.split(" "))
                
            cmd.extend([
                "-map", "0:v",
                *audio_map,
                "-vf", ",".join(vf_filters),
                "-c:v", "libx264",
                "-preset", "slow",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-r", "30",
                "-t", "20",
                "-movflags", "+faststart",
                str(final_output_path)
            ])
            
            logger.info(f"Assembling announcement video → {final_output_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg announcement assembly failed: {result.stderr}")
        else:
            # Mock build
            final_output_path.write_bytes(b"dummy_announcement_reel_content")

        job.output_path = str(final_output_path)
        
        # Cleanup B-roll files
        try:
            concat_bg_path.unlink(missing_ok=True)
            overlay_bg_path.unlink(missing_ok=True)
            for clip in clip_paths:
                clip.unlink(missing_ok=True)
        except Exception:
            pass

        _update_status(JobStatus.COMPLETED, "Announcement Reel completed successfully!")
        job.completed_at = datetime_now()
        session.add(job)
        session.commit()
        return job

    except Exception as e:
        logger.error(f"[Announcement Pipeline] Job {job.id} FAILED: {e}", exc_info=True)
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.updated_at = datetime_now()
        session.add(job)
        session.commit()
        return job


def datetime_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_announcement_ass(job_data: dict[str, Any], output_path: Path, duration: float = 20.0):
    """Write an ASS subtitle file for the job announcement reel."""
    
    company = job_data.get("company_name", "HIRING COMPANY").strip()
    role = job_data.get("job_role", "Job Role").strip()
    salary = job_data.get("salary", "").strip()
    eligibility = job_data.get("eligibility", "").strip()
    batch = job_data.get("batch", "").strip()
    experience = job_data.get("experience", "").strip()
    location = job_data.get("location", "").strip()
    work_mode = job_data.get("work_mode", "").strip()
    last_date = job_data.get("last_date", "").strip()
    cta_text = job_data.get("cta_text", "Comment 'LINK' to Apply").strip()

    # ASS Header
    ass_content = """[Script Info]
Title: Job Announcement Overlay
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TopCardBg,Arial,10,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&HFFFFFFFF,1,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1
Style: TopCard,Arial,36,&H00000000,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1
Style: Headline,Arial Black,42,&H00FFFFFF,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0,0,3,8,0,8,60,60,700,1
Style: InfoCard,Arial Black,44,&H00FFFFFF,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0,0,3,12,0,5,60,60,0,1
Style: BottomCTA,Arial Black,46,&H00000000,&H00000000,&H00FFFFFF,&HFFFFFFFF,1,0,0,0,100,100,0,0,3,12,0,2,60,60,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    # Build multi-line top card text
    top_card_lines = [
        f"{{\\fs50\\c&H000000FF&\\b1}}{company.upper()}",
        f"{{\\fs60\\c&H00000000&\\b1}}NOW HIRING",
        f"{{\\fs44\\c&H00555555&\\b1}}{role.upper()}"
    ]
    
    if eligibility:
        top_card_lines.append(f"{{\\fs36}}• Education: {eligibility}")
    if batch:
        top_card_lines.append(f"{{\\fs36}}• Batch: {batch}")
    if salary:
        top_card_lines.append(f"{{\\fs36}}• CTC: {salary}")
        
    top_card_lines.append(f"{{\\fs38\\c&H000000FF&\\b1}}[ APPLY NOW ]")
    top_card_lines.append(f"{{\\fs30\\c&H00AAAAAA&}}○   ○   ○")
    top_card_text = "\\N".join(top_card_lines)

    # 1. Top Card Background and Text dialogues (visible throughout the entire video)
    ass_content += f"Dialogue: 0,0:00:00.00,{format_time(duration)},TopCardBg,,0,0,0,,{{\\pos(120,100)\\p1}}m 35 0 l 805 0 b 822 0 840 18 840 35 l 840 565 b 840 582 822 600 805 600 l 35 600 b 18 600 0 582 0 565 l 0 35 b 0 18 18 0 35 0{{\\p0}}\n"
    ass_content += f"Dialogue: 1,0:00:00.00,{format_time(duration)},TopCard,,0,0,0,,{{\\pos(540,125)\\q2}}{top_card_text}\n"

    # 2. Headline dialogue (visible throughout the entire video)
    headline_text = f"🚨 {company.upper()} is Hiring! 🚨\\N🔥 Off Campus Drive 2026 🔥"
    ass_content += f"Dialogue: 0,0:00:00.00,{format_time(duration)},Headline,,0,0,0,,{headline_text}\n"

    # 3. Info Cards (sequential animation)
    # Collect non-empty details
    cards = []
    if role:
        cards.append(f"👩‍💻 Designation: {role}")
    if eligibility:
        cards.append(f"🎓 Eligibility: {eligibility}")
    if batch:
        cards.append(f"📅 Batch: {batch}")
    if salary:
        cards.append(f"💰 CTC: {salary}")
    if experience:
        cards.append(f"⭐ Experience: {experience}")
    if location or work_mode:
        if location and work_mode:
            cards.append(f"📍 Location: {location} ({work_mode})")
        else:
            cards.append(f"📍 Location: {location or work_mode}")
    if last_date:
        cards.append(f"⏰ Last Date: {last_date}")

    # Display sequential cards inside the [0.0, 16.0] seconds interval
    active_period = 16.0
    if cards:
        time_per_card = active_period / len(cards)
        for i, card_text in enumerate(cards):
            start = i * time_per_card
            end = start + time_per_card
            
            # Highlight values by adding color tags
            # e.g., yellow color (&H00FFFF&) for values after a colon ':'
            if ":" in card_text:
                label, val = card_text.split(":", 1)
                formatted_card = f"{label}: {{\\c&H0000FFFF&}}{val}{{\\r}}"
            else:
                formatted_card = card_text
                
            ass_content += (
                f"Dialogue: 0,{format_time(start)},{format_time(end)},InfoCard,,0,0,0,,"
                f"{{\\move(540,1230,540,1160,0,450)\\fad(400,400)}}{formatted_card}\n"
            )

    # 4. Final Big CTA Card in the center (visible from 16.0s to 20.0s)
    final_cta_main = f"{{\\c&H0000FFFF&}}👉 FOLLOW FOR DAILY JOB UPDATES! 👈\\N\\N{{\\c&H00FFFFFF&}}Comment \"LINK\" to apply"
    ass_content += (
        f"Dialogue: 0,{format_time(active_period)},{format_time(duration)},InfoCard,,0,0,0,,"
        f"{{\\move(540,1230,540,1160,0,450)\\fad(400,400)}}{final_cta_main}\n"
    )

    # 5. Bottom CTA Dialogue (visible throughout the entire video)
    bottom_cta_text = f"👉 {cta_text.upper()} 👈"
    ass_content += f"Dialogue: 0,0:00:00.00,{format_time(duration)},BottomCTA,,0,0,0,,{bottom_cta_text}\n"

    # Write ASS file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    logger.info(f"ASS generated at {output_path}")
