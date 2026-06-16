"""
OpenAI TTS voice provider implementation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from openai import AsyncOpenAI

from app.providers.voice.base import BaseVoiceProvider, VoiceInfo
from app.config import get_settings

logger = logging.getLogger(__name__)

# Available OpenAI voices
OPENAI_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


class OpenAIVoiceProvider(BaseVoiceProvider):
    """OpenAI TTS provider using tts-1-hd or gpt-4o-mini-tts."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._default_voice = settings.openai_tts_voice
        self._model = "tts-1-hd"

    @property
    def provider_name(self) -> str:
        return "OpenAI TTS"

    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        voice_id: str = "",
        language: str = "en",
        speed: float = 1.0,
    ) -> Path:
        voice = voice_id or self._default_voice

        logger.info(f"OpenAI TTS: voice={voice}, model={self._model}, len={len(text)}")

        # Build instructions based on language
        instructions = self._get_instructions(language)

        response = await self._client.audio.speech.create(
            model=self._model,
            voice=voice,
            input=text,
            speed=speed,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        response.stream_to_file(str(output_path))

        logger.info(f"OpenAI TTS audio saved: {output_path}")
        return output_path

    async def list_voices(self, language: str = "") -> list[VoiceInfo]:
        return [
            VoiceInfo(id=v, name=v.capitalize(), language=language or "en")
            for v in OPENAI_VOICES
        ]

    def _get_instructions(self, language: str) -> str:
        """Get voice instructions based on language."""
        base = "Speak clearly with natural pacing and emphasis on key information."
        if language == "hi":
            return f"{base} Speak in Hindi with a professional tone."
        elif language == "hinglish":
            return f"{base} Speak in a natural mix of Hindi and English (Hinglish) as commonly spoken in India."
        return base
