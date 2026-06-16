"""
FFmpeg wrapper utilities for video/audio processing.
"""

from __future__ import annotations

import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def check_ffmpeg() -> bool:
    """Check if FFmpeg is installed and available."""
    return shutil.which("ffmpeg") is not None


def extract_audio(
    video_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
) -> Path:
    """Extract audio from a video file as WAV.

    Args:
        video_path: Input video file.
        output_path: Output WAV file path.
        sample_rate: Audio sample rate (16kHz for Whisper).
        channels: Number of audio channels (1 for mono).

    Returns:
        Path to extracted audio file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        str(output_path),
    ]

    logger.info(f"Extracting audio: {video_path} → {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr}")

    return output_path


def extract_keyframes(
    video_path: Path,
    output_dir: Path,
    fps: float = 0.5,
) -> list[Path]:
    """Extract keyframes from a video at specified FPS.

    Args:
        video_path: Input video file.
        output_dir: Directory to save frames.
        fps: Frames per second to extract (0.5 = 1 every 2 seconds).

    Returns:
        List of paths to extracted frame images.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(output_dir / "frame_%04d.jpg")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", "2",
        pattern,
    ]

    logger.info(f"Extracting frames: {video_path} → {output_dir}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg frame extraction failed: {result.stderr}")

    frames = sorted(output_dir.glob("frame_*.jpg"))
    logger.info(f"Extracted {len(frames)} frames")
    return frames


def get_video_duration(video_path: Path) -> float:
    """Get the duration of a video file in seconds."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    return float(result.stdout.strip())


def get_audio_duration(audio_path: Path) -> float:
    """Get the duration of an audio file in seconds."""
    return get_video_duration(audio_path)


def concatenate_clips(
    clip_paths: list[Path],
    output_path: Path,
    transition: str = "fade",
    transition_duration: float = 0.5,
) -> Path:
    """Concatenate multiple video clips with transitions.

    Args:
        clip_paths: List of video clip paths.
        output_path: Output merged video path.
        transition: Transition type (fade, slide, etc.).
        transition_duration: Transition duration in seconds.

    Returns:
        Path to concatenated video.
    """
    if not clip_paths:
        raise ValueError("No clips to concatenate")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a concat demuxer file
    concat_file = output_path.parent / "concat_list.txt"
    with open(concat_file, "w") as f:
        for clip in clip_paths:
            abs_path = Path(clip).resolve()
            f.write(f"file '{abs_path.as_posix()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-r", "30",
        "-s", "1080x1920",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    logger.info(f"Concatenating {len(clip_paths)} clips → {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Clean up concat file
    concat_file.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg concatenation failed: {result.stderr}")

    return output_path


def assemble_reel(
    video_path: Path,
    voiceover_path: Path,
    captions_path: Optional[Path],
    bgm_path: Optional[Path],
    output_path: Path,
    bgm_volume: float = 0.12,
) -> Path:
    """Assemble the final reel — merge video, voiceover, captions, and BGM.

    Args:
        video_path: Concatenated scene clips video.
        voiceover_path: AI-generated voiceover audio.
        captions_path: ASS subtitle file (optional).
        bgm_path: Background music file (optional).
        output_path: Final output reel path.
        bgm_volume: BGM volume level (0.0 - 1.0).

    Returns:
        Path to the final reel.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the FFmpeg command
    inputs = ["-i", str(video_path), "-i", str(voiceover_path)]
    filter_parts = []

    if bgm_path and bgm_path.exists():
        inputs.extend(["-i", str(bgm_path)])
        # Mix voiceover (full volume) with BGM (low volume)
        filter_parts.append(f"[1:a]volume=1.0[voice];[2:a]volume={bgm_volume}[bgm];[voice][bgm]amix=inputs=2:duration=first[aout]")
        audio_map = ["-map", "[aout]"]
    else:
        audio_map = ["-map", "1:a"]

    # Video filters
    vf_filters = []
    if captions_path and captions_path.exists():
        # Burn in ASS subtitles
        ass_path = str(captions_path).replace("\\", "/").replace(":", "\\:")
        vf_filters.append(f"ass={ass_path}")

    # Ensure correct output resolution
    vf_filters.append("scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2")

    cmd = [
        "ffmpeg", "-y",
        *inputs,
    ]

    if filter_parts:
        cmd.extend(["-filter_complex", ";".join(filter_parts)])

    vf_str = ",".join(vf_filters)
    cmd.extend([
        "-map", "0:v",
        *audio_map,
        "-vf", vf_str,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", "30",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path),
    ])

    logger.info(f"Assembling final reel → {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg assembly failed: {result.stderr}")

    logger.info(f"Final reel created: {output_path}")
    return output_path


def scale_video_to_portrait(
    input_path: Path,
    output_path: Path,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Scale/crop a video to portrait 9:16 format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-an",  # No audio
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg scaling failed: {result.stderr}")

    return output_path


def trim_video(
    input_path: Path,
    output_path: Path,
    start: float,
    duration: float,
) -> Path:
    """Trim a video to a specific segment."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(input_path),
        "-t", str(duration),
        "-c", "copy",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg trim failed: {result.stderr}")

    return output_path
