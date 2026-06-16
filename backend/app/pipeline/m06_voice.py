"""
MODULE 6 — Voice Engine

Abstraction layer for TTS providers (ElevenLabs, OpenAI TTS, Cartesia).
Generates realistic AI voiceover from script text.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.config import get_settings, VoiceProvider
from app.providers.voice.base import BaseVoiceProvider
from app.providers.voice.elevenlabs import ElevenLabsVoiceProvider
from app.providers.voice.openai_tts import OpenAIVoiceProvider
from app.providers.voice.cartesia import CartesiaVoiceProvider
from app.providers.voice.mock import MockVoiceProvider
from app.utils.ffmpeg import get_audio_duration

logger = logging.getLogger(__name__)


def _get_voice_provider(provider_name: str) -> BaseVoiceProvider:
    """Factory function to get the voice provider instance."""
    settings = get_settings()

    # Determine if the provider is available
    try:
        provider_enum = VoiceProvider(provider_name)
        has_key = settings.has_voice_provider(provider_enum)
    except ValueError:
        has_key = False

    if not has_key:
        logger.warning(f"Voice provider '{provider_name}' is not configured (missing API key). Falling back to MockVoiceProvider.")
        return MockVoiceProvider()

    providers = {
        "elevenlabs": ElevenLabsVoiceProvider,
        "openai": OpenAIVoiceProvider,
        "cartesia": CartesiaVoiceProvider,
    }

    provider_cls = providers.get(provider_name)
    if not provider_cls:
        raise ValueError(f"Unknown voice provider: {provider_name}")

    return provider_cls()


def _clean_script_for_tts(script: str) -> str:
    """Remove markers and formatting from script text for TTS input.

    Removes [PAUSE], *emphasis*, [HOOK], etc.
    Converts pauses to natural commas/breaths instead of long pauses.
    """
    # Remove asterisk emphasis markers (keep the words/phrases inside)
    # Works for both *word* and **phrase** and *hyphenated-words*
    text = re.sub(r"\*+([^*]+)\*+", r"\1", script)
    
    # Normalize special Unicode spaces (narrow no-break spaces, non-breaking spaces, zero-width spaces)
    text = text.replace("\u202f", " ").replace("\u00a0", " ").replace("\u200b", "")
    
    # Normalize unicode hyphens/dashes to natural pauses or standard hyphens
    text = text.replace("\u2014", ", ").replace("\u2013", ", ") # em-dash and en-dash to natural pause
    text = text.replace("\u2011", "-") # non-breaking hyphen to standard hyphen
    
    # Normalize quotes
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    
    # Replace [PAUSE] that follows punctuation with a small space,
    # and other [PAUSE] with a comma for a short natural breath/pause.
    text = re.sub(r"([.,?!:;])\s*\[PAUSE\]\s*", r"\1 ", text)
    text = re.sub(r"\s*\[PAUSE\]\s*", ", ", text)
    
    # Remove any other section markers like [HOOK - 0-3s], [SCENE 1], etc.
    text = re.sub(r"\[[^\]]+\]", "", text)
    
    # Clean up extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text



async def generate_voice(
    script_data: dict[str, Any],
    job_id: str,
    provider_name: str | None = None,
    language: str = "en",
    voice_id: str = "",
) -> dict[str, Any]:
    """Generate voiceover audio from a script.

    Args:
        script_data: Script data from Module 5 (contains "script" key).
        job_id: Job ID for file naming.
        provider_name: Voice provider to use (default from config).
        language: Voice language.
        voice_id: Specific voice ID to use.

    Returns:
        Dict with "voice_path", "duration", "provider".
    """
    settings = get_settings()
    provider_name = provider_name or settings.default_voice_provider.value

    logger.info(f"[M6] Generating voice: provider={provider_name}, lang={language}")

    # Get the provider
    provider = _get_voice_provider(provider_name)

    # Clean script for TTS
    raw_script = script_data.get("script", "")
    clean_text = _clean_script_for_tts(raw_script)

    if not clean_text:
        raise ValueError("[M6] No script text to convert to speech")

    # Generate output path
    from app.utils.file_utils import get_job_dir
    job_dir = get_job_dir(job_id)
    output_path = job_dir / "voiceover.mp3"

    # Generate speech
    result_path = await provider.generate_speech(
        text=clean_text,
        output_path=output_path,
        voice_id=voice_id,
        language=language,
    )

    # Get duration
    try:
        duration = get_audio_duration(result_path)
    except Exception:
        duration = script_data.get("total_duration_estimate", 30)

    logger.info(f"[M6] Voice generated: path={result_path}, duration={duration:.1f}s, provider={provider_name}")

    return {
        "voice_path": str(result_path),
        "duration": duration,
        "provider": provider_name,
    }
