"""
MODULE 2 — Transcription Engine

Uses faster-whisper for Hindi/English/Hinglish transcription.
Outputs: transcript text + word-level timestamps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """A single transcription segment with timing."""
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    """Complete transcription output."""
    language: str
    segments: list[TranscriptionSegment] = field(default_factory=list)
    full_text: str = ""
    confidence: float = 0.0


async def transcribe(
    audio_path: Path,
    model_size: str = "base",
    language: str | None = None,
) -> TranscriptionResult:
    """Transcribe audio using faster-whisper.

    Args:
        audio_path: Path to the audio WAV file.
        model_size: Whisper model size (tiny, base, small, medium, large).
        language: Force language (None for auto-detect).

    Returns:
        TranscriptionResult with segments and full text.
    """
    logger.info(f"[M2] Transcribing: {audio_path}, model={model_size}")

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        segments_gen, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
        )

        segments = []
        full_text_parts = []

        for segment in segments_gen:
            seg = TranscriptionSegment(
                start=round(segment.start, 2),
                end=round(segment.end, 2),
                text=segment.text.strip(),
            )
            segments.append(seg)
            full_text_parts.append(seg.text)

        detected_lang = info.language or "en"
        confidence = info.language_probability or 0.0

        # Detect Hinglish (mixed Hindi + English)
        if detected_lang == "hi":
            full_text = " ".join(full_text_parts)
            english_chars = sum(1 for c in full_text if c.isascii() and c.isalpha())
            total_chars = sum(1 for c in full_text if c.isalpha())
            if total_chars > 0 and english_chars / total_chars > 0.3:
                detected_lang = "hinglish"

        result = TranscriptionResult(
            language=detected_lang,
            segments=segments,
            full_text=" ".join(full_text_parts),
            confidence=confidence,
        )

        logger.info(
            f"[M2] Transcription complete: lang={detected_lang}, "
            f"segments={len(segments)}, confidence={confidence:.2f}"
        )
        return result

    except ImportError:
        logger.warning("[M2] faster-whisper not installed, using OpenAI Whisper API fallback")
        return await _transcribe_openai_api(audio_path, language)


async def _transcribe_openai_api(
    audio_path: Path,
    language: str | None = None,
) -> TranscriptionResult:
    """Fallback: Use OpenAI Whisper API for transcription."""
    from openai import AsyncOpenAI
    from app.config import get_settings

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    with open(audio_path, "rb") as f:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language=language,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = []
    if hasattr(response, "segments") and response.segments:
        for seg in response.segments:
            segments.append(
                TranscriptionSegment(
                    start=seg.get("start", 0),
                    end=seg.get("end", 0),
                    text=seg.get("text", "").strip(),
                )
            )

    detected_lang = getattr(response, "language", "en") or "en"
    full_text = response.text if hasattr(response, "text") else ""

    return TranscriptionResult(
        language=detected_lang,
        segments=segments,
        full_text=full_text,
        confidence=0.9,
    )
