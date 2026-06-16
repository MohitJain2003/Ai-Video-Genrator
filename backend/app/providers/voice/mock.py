"""
Mock Voice Provider for testing and local development without active API keys.
Generates silent MP3 files matching the text's spoken duration using FFmpeg.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app.providers.voice.base import BaseVoiceProvider, VoiceInfo

logger = logging.getLogger(__name__)


class MockVoiceProvider(BaseVoiceProvider):
    """Mock voice provider generating silent audio files with correct duration."""

    @property
    def provider_name(self) -> str:
        return "Mock Voice"

    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        voice_id: str = "",
        language: str = "en",
        speed: float = 1.0,
    ) -> Path:
        # Calculate estimated duration: ~130 words per minute (2.16 words per second)
        word_count = len(text.split())
        estimated_duration = max(3.0, word_count / 2.2)

        logger.info(f"[MockVoice] Generating silent voiceover for {word_count} words (est. {estimated_duration:.1f}s)")

        # Create output directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate silent audio via FFmpeg if available, otherwise write a dummy file
        from app.utils.ffmpeg import check_ffmpeg
        if not check_ffmpeg():
            logger.warning("[MockVoice] FFmpeg not found in PATH. Writing a dummy silent file instead.")
            output_path.write_bytes(b"dummy_mp3_audio_content")
            return output_path

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", f"{estimated_duration:.2f}",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"[MockVoice] FFmpeg silent audio generation failed: {result.stderr}")
            # Fallback to dummy file
            output_path.write_bytes(b"dummy_mp3_audio_content")
            return output_path

        logger.info(f"[MockVoice] Silent voiceover saved to: {output_path}")
        return output_path

    async def list_voices(self, language: str = "") -> list[VoiceInfo]:
        return [
            VoiceInfo(id="mock-male", name="Mock Male", language=language or "en", gender="male"),
            VoiceInfo(id="mock-female", name="Mock Female", language=language or "en", gender="female"),
        ]
