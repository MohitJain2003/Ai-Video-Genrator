"""
Cartesia voice provider implementation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cartesia import Cartesia

from app.providers.voice.base import BaseVoiceProvider, VoiceInfo
from app.config import get_settings

logger = logging.getLogger(__name__)


class CartesiaVoiceProvider(BaseVoiceProvider):
    """Cartesia Sonic TTS provider."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = Cartesia(api_key=settings.cartesia_api_key)
        self._default_voice_id = settings.cartesia_voice_id
        self._model = "sonic-3.5"

    @property
    def provider_name(self) -> str:
        return "Cartesia"

    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        voice_id: str = "",
        language: str = "en",
        speed: float = 1.0,
    ) -> Path:
        vid = voice_id or self._default_voice_id

        logger.info(f"Cartesia TTS: voice={vid}, model={self._model}, len={len(text)}")

        # Cartesia SDK is synchronous
        audio_bytes = self._client.tts.bytes(
            model_id=self._model,
            transcript=text,
            voice={"mode": "id", "id": vid},
            output_format={
                "container": "mp3",
                "sample_rate": 44100,
                "bit_rate": 128000,
            },
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        logger.info(f"Cartesia audio saved: {output_path}")
        return output_path

    async def list_voices(self, language: str = "") -> list[VoiceInfo]:
        # Cartesia voice listing requires API call
        # For now return a placeholder — will be populated from dashboard
        return [
            VoiceInfo(
                id=self._default_voice_id,
                name="Default Cartesia Voice",
                language=language or "en",
            )
        ]
