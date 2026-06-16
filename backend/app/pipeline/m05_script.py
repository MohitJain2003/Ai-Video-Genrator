"""
MODULE 5 — Script Generator

Generates a conversational, high-retention reel script (20-35 seconds).
Human-sounding, natural pacing, emotional emphasis.
"""

from __future__ import annotations

import logging
from typing import Any

from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

SCRIPT_SYSTEM_PROMPT = """You are a professional short-form video scriptwriter for Indian job opportunity reels.
You write scripts that sound NATURAL and HUMAN — like a friend telling you about a job opportunity.

RULES:
1. Duration: 20-35 seconds of speaking time (approximately 80-140 words)
2. Short sentences — MAX 15 words per sentence
3. Natural pacing — include pause markers [PAUSE] where natural pauses should be
4. Conversational tone — like talking to a friend, not reading a news article
5. Include ALL key job details factually
6. End with a clear, urgent CTA (Call to Action)
7. Use emphasis markers *word* for words that should be stressed
8. No filler words, no personal opinions
9. Every sentence must provide VALUE (a fact, detail, or action)
10. DO NOT include literal website URLs (like https://... or website.com/path) inside the spoken text of the script. Instead, say 'link in description', 'link in bio', or 'apply online'. This is crucial to make the speech sound natural and human."""

SCRIPT_PROMPT_TEMPLATE = """Write a reel script using this hook and job data:

HOOK: {hook}

JOB DATA:
- Company: {company_name}
- Role: {job_role}
- Salary: {salary}
- Eligibility: {eligibility}
- Degree: {degree_requirements}
- Batch: {batch}
- Experience: {experience}
- Location: {location}
- Last Date: {last_date}
- Selection: {selection_process}
- Apply Link: {apply_link}
- Notes: {important_notes}

LANGUAGE: {language}

FORMAT your response as a JSON object:
{{
    "script": "The full script text with [PAUSE] markers and *emphasis* markers",
    "sections": [
        {{
            "type": "hook",
            "text": "hook text",
            "duration_estimate": 3,
            "start_time": 0,
            "end_time": 3
        }},
        {{
            "type": "info",
            "text": "info section text",
            "duration_estimate": 5,
            "start_time": 3,
            "end_time": 8
        }}
    ],
    "total_duration_estimate": 30,
    "word_count": 100,
    "language": "{language}"
}}

Sections should be: hook (0-3s), company_intro (3-8s), details (8-18s), urgency (18-25s), cta (25-30s).
Only include facts from the job data. Skip any field that is null/not specified."""


async def generate_script(
    job_data: dict[str, Any],
    selected_hook: str,
    llm: BaseLLMProvider,
    language: str = "hinglish",
) -> dict[str, Any]:
    """Generate a high-retention reel script.

    Args:
        job_data: Extracted job information.
        selected_hook: The chosen hook text.
        llm: LLM provider.
        language: Script language (en, hi, hinglish).

    Returns:
        Script data with sections and timing.
    """
    logger.info(f"[M5] Generating script: lang={language}, hook='{selected_hook[:40]}...'")

    # Format list fields
    degree_str = ", ".join(job_data.get("degree_requirements", [])) or "Not specified"
    selection_str = " → ".join(job_data.get("selection_process", [])) or "Not specified"
    notes_str = "; ".join(job_data.get("important_notes", [])) or "None"

    prompt = SCRIPT_PROMPT_TEMPLATE.format(
        hook=selected_hook,
        company_name=job_data.get("company_name", "Unknown"),
        job_role=job_data.get("job_role", "Unknown"),
        salary=job_data.get("salary", "Not specified"),
        eligibility=job_data.get("eligibility", "Not specified"),
        degree_requirements=degree_str,
        batch=job_data.get("batch", "Not specified"),
        experience=job_data.get("experience", "Not specified"),
        location=job_data.get("location", "Not specified"),
        last_date=job_data.get("last_date", "Not specified"),
        selection_process=selection_str,
        apply_link=job_data.get("apply_link", "Link in bio"),
        important_notes=notes_str,
        language=language,
    )

    result = await llm.generate_json(
        prompt=prompt,
        system_prompt=SCRIPT_SYSTEM_PROMPT,
        temperature=0.6,
    )

    # Validate duration estimate
    duration = result.get("total_duration_estimate", 30)
    if duration < 15 or duration > 45:
        logger.warning(f"[M5] Script duration {duration}s outside optimal range, adjusting")
        result["total_duration_estimate"] = max(20, min(35, duration))

    logger.info(
        f"[M5] Script generated: {result.get('word_count', '?')} words, "
        f"~{result.get('total_duration_estimate', '?')}s, "
        f"sections={len(result.get('sections', []))}"
    )
    return result
