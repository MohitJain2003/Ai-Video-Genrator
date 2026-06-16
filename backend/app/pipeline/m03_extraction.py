"""
MODULE 3 — Information Extraction Engine

Converts transcript/text into structured job information JSON.
Removes filler words, creator opinions, unnecessary commentary.
Keeps only factual job data.
"""

from __future__ import annotations

import logging
from typing import Any

from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are a job information extraction specialist. 
Extract ONLY factual job information from the given text.

RULES:
1. Extract ONLY facts — company name, role, salary, eligibility, etc.
2. REMOVE all filler words, creator opinions, promotional language, personal commentary.
3. If information is not mentioned, use null.
4. Dates should be in YYYY-MM-DD format when possible.
5. Salary should include currency/unit (e.g., "3.6 LPA", "₹25,000/month").
6. Always respond with valid JSON only."""

EXTRACTION_PROMPT_TEMPLATE = """Extract structured job information from the following text:

---
{text}
---

Return a JSON object with EXACTLY these fields:
{{
    "company_name": "string or null",
    "job_role": "string or null",
    "salary": "string or null",
    "eligibility": "string or null",
    "degree_requirements": ["list of degrees or null"],
    "batch": "string (graduation years) or null",
    "experience": "string or null",
    "location": "string or null",
    "last_date": "string (YYYY-MM-DD if possible) or null",
    "selection_process": ["list of steps or null"],
    "apply_link": "string URL or null",
    "important_notes": ["list of important notes or null"]
}}

Extract ONLY what is explicitly stated. Do NOT infer or make up information."""


async def extract_job_info(
    text: str,
    llm: BaseLLMProvider,
) -> dict[str, Any]:
    """Extract structured job information from raw text.

    Args:
        text: Transcript, article text, or PDF text.
        llm: LLM provider to use for extraction.

    Returns:
        Structured job data dictionary.
    """
    logger.info(f"[M3] Extracting job info: {len(text)} chars of text")

    prompt = EXTRACTION_PROMPT_TEMPLATE.format(text=text[:8000])  # Limit context

    job_data = await llm.generate_json(
        prompt=prompt,
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
        temperature=0.1,
    )

    # Normalize and validate
    job_data = _normalize_job_data(job_data)

    logger.info(f"[M3] Extracted: company={job_data.get('company_name')}, role={job_data.get('job_role')}")
    return job_data


def extract_from_manual(manual_data: dict[str, Any]) -> dict[str, Any]:
    """Convert manual form input to standard job data format.

    Args:
        manual_data: Dict from ManualJobInput schema.

    Returns:
        Normalized job data dictionary.
    """
    return _normalize_job_data(manual_data)


def _normalize_job_data(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize and clean job data fields."""
    fields = [
        "company_name", "job_role", "salary", "eligibility",
        "batch", "experience", "location", "last_date", "apply_link",
    ]
    list_fields = ["degree_requirements", "selection_process", "important_notes"]

    normalized = {}
    for f in fields:
        val = data.get(f)
        if val and isinstance(val, str) and val.lower() in ("null", "none", "n/a", "not mentioned", "not specified"):
            val = None
        normalized[f] = val

    for f in list_fields:
        val = data.get(f)
        if isinstance(val, list):
            normalized[f] = [str(v) for v in val if v]
        elif val is None:
            normalized[f] = []
        else:
            normalized[f] = [str(val)] if val else []

    return normalized
