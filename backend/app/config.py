"""
Application configuration loaded from environment variables.
Uses pydantic-settings for type-safe config with .env file support.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    GROQ = "groq"
    SAMBANOVA = "sambanova"
    CEREBRAS = "cerebras"
    GEMINI = "gemini"


class VoiceProvider(str, Enum):
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    CARTESIA = "cartesia"


class VideoProvider(str, Enum):
    VEO = "veo"
    KLING = "kling"
    RUNWAY = "runway"
    PEXELS = "pexels"


class VoiceLanguage(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hinglish"


class Settings(BaseSettings):
    """Application settings with environment variable binding."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_env: Environment = Environment.DEVELOPMENT
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "sqlite:///./storage/db/reelgen.db"

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── AI / LLM ─────────────────────────────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    sambanova_api_key: str = ""
    cerebras_api_key: str = ""

    # ── Voice ────────────────────────────────────────────────────
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "TX3LPaxmHKxFdv7VOQHJ"
    openai_tts_voice: str = "onyx"
    cartesia_api_key: str = ""
    cartesia_voice_id: str = ""

    # ── Video Generation ─────────────────────────────────────────
    google_api_key: str = ""
    runwayml_api_secret: str = ""
    kling_api_key: str = ""

    # ── Stock Footage ────────────────────────────────────────────
    pexels_api_key: str = ""

    # ── Storage ──────────────────────────────────────────────────
    storage_path: str = "./storage"

    # ── Default Providers ────────────────────────────────────────
    default_llm_provider: LLMProvider = LLMProvider.GROQ
    default_voice_provider: VoiceProvider = VoiceProvider.ELEVENLABS
    default_video_provider: VideoProvider = VideoProvider.PEXELS
    default_voice_language: VoiceLanguage = VoiceLanguage.HINGLISH

    # ── Quality ──────────────────────────────────────────────────
    quality_threshold: int = 75
    max_retries: int = 1

    # ── Whisper ──────────────────────────────────────────────────
    whisper_model_size: str = "base"  # tiny, base, small, medium, large

    @property
    def storage_dir(self) -> Path:
        return Path(self.storage_path)

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def audio_dir(self) -> Path:
        return self.storage_dir / "audio"

    @property
    def voice_dir(self) -> Path:
        return self.storage_dir / "voice"

    @property
    def visuals_dir(self) -> Path:
        return self.storage_dir / "visuals"

    @property
    def captions_dir(self) -> Path:
        return self.storage_dir / "captions"

    @property
    def output_dir(self) -> Path:
        return self.storage_dir / "output"

    @property
    def db_dir(self) -> Path:
        return self.storage_dir / "db"

    def ensure_storage_dirs(self) -> None:
        """Create all required storage directories."""
        for d in [
            self.uploads_dir,
            self.audio_dir,
            self.voice_dir,
            self.visuals_dir,
            self.captions_dir,
            self.output_dir,
            self.db_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def has_llm_provider(self, provider: LLMProvider) -> bool:
        if provider == LLMProvider.OPENAI:
            return bool(self.openai_api_key)
        if provider == LLMProvider.CLAUDE:
            return bool(self.anthropic_api_key)
        if provider == LLMProvider.GROQ:
            return bool(self.groq_api_key)
        if provider == LLMProvider.SAMBANOVA:
            return bool(self.sambanova_api_key)
        if provider == LLMProvider.CEREBRAS:
            return bool(self.cerebras_api_key)
        if provider == LLMProvider.GEMINI:
            return bool(self.google_api_key)
        return False

    def has_voice_provider(self, provider: VoiceProvider) -> bool:
        if provider == VoiceProvider.ELEVENLABS:
            return bool(self.elevenlabs_api_key)
        if provider == VoiceProvider.OPENAI:
            return bool(self.openai_api_key)
        if provider == VoiceProvider.CARTESIA:
            return bool(self.cartesia_api_key)
        return False

    def has_video_provider(self, provider: VideoProvider) -> bool:
        if provider == VideoProvider.VEO:
            return bool(self.google_api_key)
        if provider == VideoProvider.KLING:
            return bool(self.kling_api_key)
        if provider == VideoProvider.RUNWAY:
            return bool(self.runwayml_api_secret)
        if provider == VideoProvider.PEXELS:
            return bool(self.pexels_api_key)
        return False


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    settings = Settings()
    settings.ensure_storage_dirs()
    return settings
