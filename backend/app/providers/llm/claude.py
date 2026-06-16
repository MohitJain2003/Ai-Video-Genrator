"""
Anthropic Claude LLM provider implementation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from app.providers.llm.base import BaseLLMProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


class ClaudeLLMProvider(BaseLLMProvider):
    """Anthropic Claude-based LLM provider."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = "claude-sonnet-4-20250514"

    @property
    def provider_name(self) -> str:
        return "Claude"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: str = "text",
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        logger.info(f"Claude generate: model={self._model}, tokens={max_tokens}")
        response = await self._client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        logger.info(f"Claude response: {len(content)} chars")
        return content

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        if not system_prompt:
            system_prompt = (
                "You are a structured data extraction assistant. "
                "Always respond with valid JSON only. No markdown, no code fences, no explanation."
            )

        raw = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )

        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from Claude: {cleaned[:200]}")
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(cleaned[start:end])
            raise ValueError(f"Claude did not return valid JSON: {cleaned[:200]}")
