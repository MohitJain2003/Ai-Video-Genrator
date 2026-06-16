"""
Abstract base class for Voice/TTS providers.
All voice providers (ElevenLabs, OpenAI TTS, Cartesia) must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VoiceInfo:
    """Metadata about a voice."""
    id: str
    name: str
    language: str
    gender: str = "neutral"
    preview_url: str = ""


class BaseVoiceProvider(ABC):
    """Abstract voice/TTS provider interface."""

    @abstractmethod
    async def generate_speech(
        self,
        text: str,
        output_path: Path,
        voice_id: str = "",
        language: str = "en",
        speed: float = 1.0,
    ) -> Path:
        """Generate speech audio from text.

        Args:
            text: The script text to convert to speech.
            output_path: Where to save the output audio file.
            voice_id: Provider-specific voice identifier.
            language: Language code (en, hi, hinglish).
            speed: Speech speed multiplier.

        Returns:
            Path to the generated audio file.
        """
        ...

    @abstractmethod
    async def list_voices(self, language: str = "") -> list[VoiceInfo]:
        """List available voices, optionally filtered by language.

        Args:
            language: Filter by language code.

        Returns:
            List of available voices.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...
