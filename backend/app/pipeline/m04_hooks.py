"""
MODULE 4 — Hook Generator

Generates 10 hook variations, scores each, and selects the best one.
Hooks are designed to stop scrolling and maximize engagement.
"""

from __future__ import annotations

import logging
from typing import Any

from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

HOOK_SYSTEM_PROMPT = """You are a viral social media content strategist specializing in job opportunity reels.
You create scroll-stopping hooks that make viewers watch the entire reel.

Your hooks must:
1. Create IMMEDIATE urgency or curiosity
2. Be under 15 words
3. Feel conversational, not clickbaity
4. Reference specific job details when available
5. Target fresh graduates and job seekers in India"""

HOOK_PROMPT_TEMPLATE = """Generate 10 unique hook variations for a job reel with these details:

Company: {company_name}
Role: {job_role}
Salary: {salary}
Eligibility: {eligibility}
Batch: {batch}
Experience: {experience}
Last Date: {last_date}

For each hook, provide:
- The hook text
- A score from 0-100 based on:
  - Scroll-stop power (40%): Would someone stop scrolling?
  - Relevance (30%): Does it relate to this specific job?
  - Emotional trigger (20%): Does it create urgency/curiosity/excitement?
  - Length optimization (10%): Is it concise and punchy?

Return JSON:
{{
    "hooks": [
        {{
            "text": "hook text here",
            "score": 85,
            "reasoning": "brief explanation"
        }}
    ]
}}

Make hooks varied — some urgency-based, some curiosity-based, some direct, some question-based.
Examples of great hooks:
- "Stop scrolling if you're from 2025 batch."
- "₹6 LPA without any experience? Yes, it's real."
- "Most freshers will miss this TCS hiring drive."
- "Before applying anywhere else, watch this."
- "This company just opened 5000+ positions."
"""


async def generate_hooks(
    job_data: dict[str, Any],
    llm: BaseLLMProvider,
) -> dict[str, Any]:
    """Generate 10 hook variations with scores and select the best one.

    Args:
        job_data: Extracted job information.
        llm: LLM provider.

    Returns:
        Dict with "hooks" list and "selected" best hook.
    """
    logger.info(f"[M4] Generating hooks for: {job_data.get('company_name')} — {job_data.get('job_role')}")

    prompt = HOOK_PROMPT_TEMPLATE.format(
        company_name=job_data.get("company_name", "Unknown Company"),
        job_role=job_data.get("job_role", "Unknown Role"),
        salary=job_data.get("salary", "Not specified"),
        eligibility=job_data.get("eligibility", "Not specified"),
        batch=job_data.get("batch", "Not specified"),
        experience=job_data.get("experience", "Not specified"),
        last_date=job_data.get("last_date", "Not specified"),
    )

    result = await llm.generate_json(
        prompt=prompt,
        system_prompt=HOOK_SYSTEM_PROMPT,
        temperature=0.8,
    )

    hooks = result.get("hooks", [])

    # Ensure we have hooks
    if not hooks:
        logger.warning("[M4] No hooks generated, using fallback")
        hooks = [
            {"text": f"{job_data.get('company_name', 'This company')} is hiring freshers right now!", "score": 70, "reasoning": "fallback"},
        ]

    # Sort by score descending
    hooks.sort(key=lambda h: h.get("score", 0), reverse=True)

    # Select the best hook
    best_hook = hooks[0]["text"]

    # Add index to each hook
    for i, hook in enumerate(hooks):
        hook["index"] = i
        hook["is_selected"] = (i == 0)

    logger.info(f"[M4] Generated {len(hooks)} hooks, best: '{best_hook[:50]}...' (score: {hooks[0].get('score')})")

    return {
        "hooks": hooks,
        "selected": best_hook,
        "selected_index": 0,
    }
