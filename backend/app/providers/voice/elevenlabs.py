"""
ElevenLabs voice provider implementation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

from app.providers.voice.base import BaseVoiceProvider, VoiceInfo
from app.config import get_settings

logger = logging.getLogger(__name__)


class ElevenLabsVoiceProvider(BaseVoiceProvider):
    """ElevenLabs TTS provider using eleven_multilingual_v2 model."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        self._default_voice_id = settings.elevenlabs_voice_id
        self._model = "eleven_multilingual_v2"

    @property
    def provider_name(self) -> str:
        return "ElevenLabs"

    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        voice_id: str = "",
        language: str = "en",
        speed: float = 1.0,
    ) -> Path:
        vid = voice_id or self._default_voice_id

        logger.info(f"ElevenLabs TTS: voice={vid}, model={self._model}, len={len(text)}")

        # ElevenLabs SDK is synchronous — run in thread pool in production
        audio_generator = self._client.text_to_speech.convert(
            text=text,
            voice_id=vid,
            model_id=self._model,
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.65,
                similarity_boost=0.85,
                style=0.0,
                use_speaker_boost=True,
            )
        )


        # Write audio chunks to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)

        logger.info(f"ElevenLabs audio saved: {output_path}")
        return output_path

    async def list_voices(self, language: str = "") -> list[VoiceInfo]:
        try:
            response = self._client.voices.get_all()
            voices = []
            for voice in response.voices:
                voices.append(
                    VoiceInfo(
                        id=voice.voice_id,
                        name=voice.name,
                        language=language or "en",
                        gender=voice.labels.get("gender", "neutral") if voice.labels else "neutral",
                    )
                )
            if voices:
                return voices
        except Exception as e:
            logger.warning(f"Failed to fetch voices from ElevenLabs API: {e}. Falling back to pre-configured voices.")
        
        return [
            VoiceInfo(id="TX3LPaxmHKxFdv7VOQHJ", name="Liam (Energetic Male)", language="en", gender="male"),
            VoiceInfo(id="EXAVITQu4vr4xnSDxMaL", name="Sarah (Mature Female)", language="en", gender="female"),
            VoiceInfo(id="IKne3meq5aSn9XLyUdCD", name="Charlie (Deep Energetic)", language="en", gender="male"),
            VoiceInfo(id="FGY2WhTYpPnrIDTdsKH5", name="Laura (Enthusiastic Female)", language="en", gender="female"),
            VoiceInfo(id="JBFqnCBsd6RMkjVDRZzb", name="George (Warm Storyteller)", language="en", gender="male"),
            VoiceInfo(id="pNInz6obpgDQGcFmaJgB", name="Adam (Firm Male)", language="en", gender="male"),
            VoiceInfo(id="cgSgspJ2msm6clMCkdW9", name="Jessica (Playful Female)", language="en", gender="female"),
        ]
