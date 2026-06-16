"""
MODULE 8 — Caption Engine

Generates ASS (Advanced SubStation Alpha) subtitles for the reel.
Features: large fonts, mobile safe zones, keyword highlighting.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ASS subtitle header template
ASS_HEADER = """[Script Info]
Title: Job Reel Captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,2,2,40,40,200,1
Style: Highlight,Arial Black,76,&H0000FFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,2,2,40,40,200,1
Style: Company,Arial Black,80,&H0000D7FF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,2,2,40,40,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Keywords that should be highlighted in captions
HIGHLIGHT_KEYWORDS = [
    "salary", "lpa", "ctc", "package", "₹",
    "eligibility", "eligible",
    "deadline", "last date", "apply",
    "fresher", "experience",
]


def _format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format (H:MM:SS.CC)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _should_highlight(word: str, company_name: str = "") -> bool:
    """Check if a word should be highlighted in captions."""
    word_lower = word.lower().strip(".,!?;:")
    if any(kw in word_lower for kw in HIGHLIGHT_KEYWORDS):
        return True
    if company_name and company_name.lower() in word_lower:
        return True
    # Highlight numbers that look like salary
    if re.match(r"[\d.,]+\s*(lpa|lakh|crore|k)", word_lower):
        return True
    return False


async def generate_captions(
    script_data: dict[str, Any],
    job_data: dict[str, Any],
    job_id: str,
    voice_duration: float = 30,
) -> dict[str, Any]:
    """Generate ASS subtitle captions for the reel.

    Args:
        script_data: Script data from Module 5.
        job_data: Extracted job data for keyword detection.
        job_id: Job ID for file naming.
        voice_duration: Actual voiceover duration for timing.

    Returns:
        Dict with "captions_path" and "word_count".
    """
    logger.info(f"[M8] Generating captions: duration={voice_duration}s")

    company_name = job_data.get("company_name", "")
    script_text = script_data.get("script", "")

    # Clean script text for captioning
    clean_text = re.sub(r"\[PAUSE\]", "", script_text)
    clean_text = re.sub(r"\*(\w+)\*", r"\1", clean_text)
    clean_text = re.sub(r"\[[\w\s\-–:]+\]", "", clean_text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # Split into caption groups (5-7 words each)
    words = clean_text.split()
    caption_groups = []
    group = []
    for word in words:
        group.append(word)
        if len(group) >= 6 or (len(group) >= 4 and word.endswith((".", "!", "?"))):
            caption_groups.append(" ".join(group))
            group = []
    if group:
        caption_groups.append(" ".join(group))

    # Calculate timing per group
    if not caption_groups:
        caption_groups = ["No captions available"]

    time_per_group = voice_duration / len(caption_groups)

    # Generate ASS events
    ass_content = ASS_HEADER
    current_time = 0.0

    for caption_text in caption_groups:
        start_time = current_time
        end_time = min(current_time + time_per_group, voice_duration)

        # Check for highlighting
        style = "Default"
        highlighted_text = caption_text

        # Apply word-level highlighting using ASS override tags
        words_in_caption = caption_text.split()
        formatted_words = []
        for w in words_in_caption:
            if _should_highlight(w, company_name):
                # Yellow highlight with larger font
                formatted_words.append(f"{{\\c&H00FFFF&\\fs80}}{w}{{\\r}}")
                style = "Default"
            elif company_name and company_name.lower() in w.lower():
                # Orange for company name
                formatted_words.append(f"{{\\c&H00A5FF&\\fs84}}{w}{{\\r}}")
            else:
                formatted_words.append(w)

        final_text = " ".join(formatted_words)

        # Limit to 2 lines
        if len(final_text) > 40:
            mid = len(words_in_caption) // 2
            line1 = " ".join(formatted_words[:mid])
            line2 = " ".join(formatted_words[mid:])
            final_text = f"{line1}\\N{line2}"

        ass_content += (
            f"Dialogue: 0,{_format_ass_time(start_time)},{_format_ass_time(end_time)},"
            f"{style},,0,0,0,,{final_text}\n"
        )

        current_time = end_time

    # Write ASS file
    from app.utils.file_utils import get_job_dir
    job_dir = get_job_dir(job_id)
    captions_path = job_dir / "captions.ass"
    captions_path.parent.mkdir(parents=True, exist_ok=True)

    with open(captions_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    logger.info(f"[M8] Captions generated: {len(caption_groups)} groups, path={captions_path}")

    return {
        "captions_path": str(captions_path),
        "caption_count": len(caption_groups),
        "word_count": len(words),
    }
