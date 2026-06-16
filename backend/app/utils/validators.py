"""
Input validators for URLs, files, and manual data.
"""

from __future__ import annotations

import re
from typing import Optional


def validate_instagram_url(url: str) -> bool:
    """Validate an Instagram reel/post URL."""
    pattern = r"https?://(www\.)?instagram\.com/(reel|p|reels)/[\w\-]+"
    return bool(re.match(pattern, url))


def validate_youtube_url(url: str) -> bool:
    """Validate a YouTube URL (shorts, watch, youtu.be)."""
    patterns = [
        r"https?://(www\.)?youtube\.com/shorts/[\w\-]+",
        r"https?://(www\.)?youtube\.com/watch\?v=[\w\-]+",
        r"https?://youtu\.be/[\w\-]+",
    ]
    return any(re.match(p, url) for p in patterns)


def validate_url(url: str) -> bool:
    """Validate any HTTP(S) URL."""
    pattern = r"https?://[^\s<>\"]+|www\.[^\s<>\"]+"
    return bool(re.match(pattern, url))


def validate_job_data(data: dict) -> tuple[bool, Optional[str]]:
    """Validate extracted job data for completeness.

    Returns:
        (is_valid, error_message)
    """
    required = ["company_name", "job_role"]
    missing = [f for f in required if not data.get(f)]

    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    return True, None
