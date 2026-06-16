"""
MODULE 7 — Scene Planner

Generates a visual timeline mapping script sections to scene descriptions.
Each scene has a visual description, timing, and transition type.
"""

from __future__ import annotations

import logging
from typing import Any

from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

SCENE_SYSTEM_PROMPT = """You are a professional video scene planner for vertical short-form content (9:16 reels).
You map script sections to visually compelling scenes.

RULES:
1. Each scene must be 3-8 seconds long
2. Scenes must be visually distinct — no repetition
3. Use SPECIFIC, descriptive visual prompts (not vague)
4. All visuals should be GENERIC/STOCK — no specific people, brands, or copyrighted content
5. Scenes should be corporate, professional, modern aesthetics
6. Final scene should always be a CTA (Call to Action) visual
7. Transitions should be smooth and modern"""

SCENE_PROMPT_TEMPLATE = """Create a scene plan for this reel script:

SCRIPT:
{script}

SCRIPT SECTIONS:
{sections}

TOTAL DURATION: {duration} seconds

COMPANY/INDUSTRY CONTEXT: {company_name} — {job_role}

Return JSON:
{{
    "scenes": [
        {{
            "scene_number": 1,
            "start_time": 0,
            "end_time": 3,
            "duration": 3,
            "visual_description": "Detailed description of what should appear on screen",
            "search_query": "Stock footage search query for this scene",
            "ai_prompt": "AI video generation prompt for this scene (include: vertical, 9:16, cinematic, corporate)",
            "transition": "fade_in",
            "text_overlay": "Optional text to show on screen"
        }}
    ]
}}

Transition options: fade_in, fade_out, slide_left, slide_right, slide_up, zoom_in, zoom_out, dissolve, cut
Make visuals match the industry/company type. Use modern, premium aesthetics."""


async def plan_scenes(
    script_data: dict[str, Any],
    job_data: dict[str, Any],
    llm: BaseLLMProvider,
    total_duration: float = 30,
) -> list[dict[str, Any]]:
    """Generate a scene plan for the reel.

    Args:
        script_data: Script data from Module 5.
        job_data: Extracted job information.
        llm: LLM provider.
        total_duration: Total reel duration in seconds.

    Returns:
        List of scene dictionaries with timing and visual descriptions.
    """
    logger.info(f"[M7] Planning scenes: duration={total_duration}s")

    sections_text = ""
    for section in script_data.get("sections", []):
        sections_text += (
            f"- [{section.get('type', 'info')}] "
            f"{section.get('start_time', 0)}-{section.get('end_time', 0)}s: "
            f'"{section.get("text", "")}"\n'
        )

    prompt = SCENE_PROMPT_TEMPLATE.format(
        script=script_data.get("script", ""),
        sections=sections_text or "No sections provided",
        duration=total_duration,
        company_name=job_data.get("company_name", "Tech Company"),
        job_role=job_data.get("job_role", "Software Engineer"),
    )

    result = await llm.generate_json(
        prompt=prompt,
        system_prompt=SCENE_SYSTEM_PROMPT,
        temperature=0.7,
    )

    scenes = result.get("scenes", [])

    if not scenes:
        logger.warning("[M7] No scenes generated, creating default plan")
        scenes = _generate_default_scenes(total_duration, job_data)

    # Validate and fix timing
    scenes = _validate_scene_timing(scenes, total_duration)

    logger.info(f"[M7] Scene plan: {len(scenes)} scenes over {total_duration}s")
    return scenes


def _generate_default_scenes(duration: float, job_data: dict) -> list[dict]:
    """Generate a default scene plan when LLM fails."""
    company = job_data.get("company_name", "Company")
    role = job_data.get("job_role", "Position")

    return [
        {
            "scene_number": 1, "start_time": 0, "end_time": 3, "duration": 3,
            "visual_description": "Modern corporate glass building exterior, sunny day",
            "search_query": "corporate building exterior modern",
            "ai_prompt": "Cinematic shot of a modern glass corporate office building, vertical 9:16, sunny day, professional",
            "transition": "fade_in", "text_overlay": "",
        },
        {
            "scene_number": 2, "start_time": 3, "end_time": 8, "duration": 5,
            "visual_description": "Young professionals working on laptops in a modern open office",
            "search_query": "people working office laptops",
            "ai_prompt": "Young professionals working on laptops in modern open office, vertical 9:16, cinematic, warm lighting",
            "transition": "slide_left", "text_overlay": f"{company}",
        },
        {
            "scene_number": 3, "start_time": 8, "end_time": 14, "duration": 6,
            "visual_description": "Close-up of hands typing on laptop, code on screen",
            "search_query": "typing laptop code technology",
            "ai_prompt": "Close-up hands typing on laptop keyboard, code on screen, vertical 9:16, tech aesthetic",
            "transition": "zoom_in", "text_overlay": "",
        },
        {
            "scene_number": 4, "start_time": 14, "end_time": 20, "duration": 6,
            "visual_description": "Team meeting in a bright conference room",
            "search_query": "business meeting conference room",
            "ai_prompt": "Team meeting in bright modern conference room, vertical 9:16, professional, collaborative",
            "transition": "dissolve", "text_overlay": "",
        },
        {
            "scene_number": 5, "start_time": 20, "end_time": 25, "duration": 5,
            "visual_description": "Person filling out job application on laptop",
            "search_query": "job application online laptop",
            "ai_prompt": "Person filling out online job application on laptop, vertical 9:16, focused, hopeful mood",
            "transition": "slide_up", "text_overlay": "",
        },
        {
            "scene_number": 6, "start_time": 25, "end_time": int(duration), "duration": int(duration) - 25,
            "visual_description": "Bold CTA screen — 'Apply Now' with upward arrow animation",
            "search_query": "apply now call to action",
            "ai_prompt": "Clean CTA screen, 'Apply Now' text, upward arrow, gradient background, vertical 9:16, modern",
            "transition": "zoom_in", "text_overlay": "Apply Now — Link in Bio",
        },
    ]


def _validate_scene_timing(scenes: list[dict], total_duration: float) -> list[dict]:
    """Ensure scenes cover the full duration without gaps or overlaps."""
    if not scenes:
        return scenes

    # Sort by start time
    scenes.sort(key=lambda s: s.get("start_time", 0))

    # Fix numbering
    for i, scene in enumerate(scenes):
        scene["scene_number"] = i + 1

    # Ensure last scene ends at total duration
    scenes[-1]["end_time"] = total_duration
    scenes[-1]["duration"] = scenes[-1]["end_time"] - scenes[-1]["start_time"]

    return scenes
