"""
OpenAI LLM provider implementation (GPT-4o / GPT-4o-mini).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.providers.llm.base import BaseLLMProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


import asyncio
import openai

class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI and OpenAI-compatible LLM provider."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        model_mini: str | None = None,
        provider_name: str = "OpenAI",
    ) -> None:
        settings = get_settings()
        key = api_key or settings.openai_api_key
        self._client = AsyncOpenAI(api_key=key, base_url=base_url)
        self._model = model or "gpt-4o"
        self._model_mini = model_mini or model or "gpt-4o-mini"
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: str = "text",
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        logger.info(f"OpenAI generate: model={self._model}, tokens={max_tokens}")
        
        max_attempts = 3
        backoff_sec = 2.0
        for attempt in range(max_attempts):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                logger.info(f"OpenAI response: {len(content)} chars")
                return content
            except Exception as e:
                is_rate_limit = False
                if isinstance(e, openai.RateLimitError):
                    is_rate_limit = True
                elif "rate limit" in str(e).lower() or "429" in str(e):
                    is_rate_limit = True
                
                if is_rate_limit and attempt < max_attempts - 1:
                    sleep_time = backoff_sec * (2 ** attempt)
                    logger.warning(
                        f"Rate limit hit on {self._provider_name} ({self._model}). "
                        f"Retrying in {sleep_time:.1f}s (attempt {attempt + 1}/{max_attempts}). Error: {e}"
                    )
                    await asyncio.sleep(sleep_time)
                else:
                    raise e

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        raw = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt or "You are a structured data extraction assistant. Always respond with valid JSON.",
            temperature=temperature,
            response_format="json",
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from OpenAI: {raw[:200]}")
            # Try to extract JSON from the response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
            raise ValueError(f"OpenAI did not return valid JSON: {raw[:200]}")
