"""
MODULE 12 — Quality Engine

Scores the final reel on hook quality, retention, readability, and CTA effectiveness.
Only outputs the final reel if the composite score is ≥ 90.
"""

from __future__ import annotations

import logging
from typing import Any

from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

QUALITY_SYSTEM_PROMPT = """You are a professional social media content quality analyst.
You evaluate short-form vertical video reels for maximum engagement and effectiveness.
Be strict but fair. Score based on proven engagement metrics."""

QUALITY_PROMPT_TEMPLATE = """Evaluate this job reel content for quality and engagement potential:

HOOK: {hook}

FULL SCRIPT:
{script}

JOB DATA COVERED:
- Company: {company_name}
- Role: {job_role}
- Salary: {salary}
- Eligibility: {eligibility}
- Last Date: {last_date}

NUMBER OF SCENES: {num_scenes}
TOTAL DURATION: {duration}s

Rate each dimension from 0-100 and provide brief reasoning:

Return JSON:
{{
    "hook_quality": {{
        "score": 0-100,
        "reasoning": "Why this score for scroll-stop power, curiosity, and engagement"
    }},
    "retention_score": {{
        "score": 0-100,
        "reasoning": "Why this score for pacing, info density, and watch-through rate"
    }},
    "readability": {{
        "score": 0-100,
        "reasoning": "Why this score for clarity, simplicity, and comprehension"
    }},
    "cta_effectiveness": {{
        "score": 0-100,
        "reasoning": "Why this score for call-to-action clarity and urgency"
    }},
    "improvement_suggestions": [
        "Suggestion 1",
        "Suggestion 2"
    ]
}}

Scoring guide:
- 90-100: Exceptional, viral potential
- 80-89: Very good, strong engagement
- 70-79: Good, solid content
- 60-69: Average, needs improvement
- Below 60: Poor, should be regenerated"""


async def evaluate_quality(
    hook: str,
    script: str,
    job_data: dict[str, Any],
    scene_plan: list[dict[str, Any]],
    duration: float,
    llm: BaseLLMProvider,
) -> dict[str, Any]:
    """Evaluate the quality of the generated reel content.

    Args:
        hook: The selected hook text.
        script: The full generated script.
        job_data: Extracted job information.
        scene_plan: Scene plan with timing.
        duration: Total reel duration.
        llm: LLM provider.

    Returns:
        Quality scores with overall composite score.
    """
    logger.info("[M12] Evaluating reel quality")

    prompt = QUALITY_PROMPT_TEMPLATE.format(
        hook=hook,
        script=script,
        company_name=job_data.get("company_name", "Unknown"),
        job_role=job_data.get("job_role", "Unknown"),
        salary=job_data.get("salary", "Not specified"),
        eligibility=job_data.get("eligibility", "Not specified"),
        last_date=job_data.get("last_date", "Not specified"),
        num_scenes=len(scene_plan),
        duration=duration,
    )

    result = await llm.generate_json(
        prompt=prompt,
        system_prompt=QUALITY_SYSTEM_PROMPT,
        temperature=0.3,
    )

    # Calculate composite score (weighted average)
    weights = {
        "hook_quality": 0.30,
        "retention_score": 0.30,
        "readability": 0.20,
        "cta_effectiveness": 0.20,
    }

    scores = {}
    overall = 0.0

    for dim, weight in weights.items():
        dim_data = result.get(dim, {})
        score = dim_data.get("score", 70) if isinstance(dim_data, dict) else dim_data
        score = max(0, min(100, float(score)))
        scores[dim] = {
            "score": score,
            "reasoning": dim_data.get("reasoning", "") if isinstance(dim_data, dict) else "",
        }
        overall += score * weight

    scores["overall_score"] = round(overall, 1)
    scores["improvement_suggestions"] = result.get("improvement_suggestions", [])

    logger.info(
        f"[M12] Quality scores: "
        f"hook={scores['hook_quality']['score']}, "
        f"retention={scores['retention_score']['score']}, "
        f"readability={scores['readability']['score']}, "
        f"cta={scores['cta_effectiveness']['score']}, "
        f"OVERALL={scores['overall_score']}"
    )

    return scores


def should_regenerate(
    quality_scores: dict[str, Any],
    threshold: int = 90,
    current_retry: int = 0,
    max_retries: int = 3,
) -> bool:
    """Determine if the reel should be regenerated based on quality scores.

    Returns:
        True if regeneration is needed and retries are available.
    """
    overall = quality_scores.get("overall_score", 0)

    if overall >= threshold:
        logger.info(f"[M12] Quality PASSED: {overall} ≥ {threshold}")
        return False

    if current_retry >= max_retries:
        logger.warning(f"[M12] Quality FAILED but max retries ({max_retries}) reached. Accepting score {overall}.")
        return False

    logger.info(f"[M12] Quality BELOW threshold: {overall} < {threshold}. Retry {current_retry + 1}/{max_retries}")
    return True
