from __future__ import annotations

import logging
from typing import Any

from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class FallbackLLMProvider(BaseLLMProvider):
    """An LLM provider that wraps a primary provider and a list of fallback providers.
    If the current provider fails, it automatically switches to the next configured provider.
    """

    def __init__(
        self,
        primary: BaseLLMProvider,
        fallbacks: list[BaseLLMProvider],
        on_fallback_success: callable | None = None,
    ) -> None:
        self.primary = primary
        self.fallbacks = fallbacks
        self._current = primary
        self._on_fallback_success = on_fallback_success

    @property
    def provider_name(self) -> str:
        return self._current.provider_name

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: str = "text",
    ) -> str:
        try:
            return await self._current.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
        except Exception as e:
            logger.warning(
                f"LLM provider {self._current.provider_name} failed: {e}. Attempting fallbacks."
            )
            # Try all fallback providers
            for provider in self.fallbacks:
                if provider.provider_name == self._current.provider_name:
                    continue
                try:
                    logger.info(f"Trying fallback LLM provider: {provider.provider_name}")
                    result = await provider.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format,
                    )
                    # Switch current working provider
                    old_provider_name = self._current.provider_name
                    self._current = provider
                    logger.info(
                        f"Successfully switched to fallback LLM: {provider.provider_name} (was: {old_provider_name})"
                    )
                    if self._on_fallback_success:
                        self._on_fallback_success(provider)
                    return result
                except Exception as fe:
                    logger.warning(f"Fallback LLM {provider.provider_name} failed: {fe}")

            # Also try primary if we were already using a fallback and it failed
            if self._current.provider_name != self.primary.provider_name:
                try:
                    logger.info(f"Retrying primary LLM provider: {self.primary.provider_name}")
                    result = await self.primary.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format,
                    )
                    self._current = self.primary
                    logger.info(f"Successfully returned to primary LLM: {self.primary.provider_name}")
                    return result
                except Exception as pe:
                    logger.warning(f"Primary LLM retry failed: {pe}")

            # Raise original error if everything failed
            raise e

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        try:
            return await self._current.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
            )
        except Exception as e:
            logger.warning(
                f"LLM provider {self._current.provider_name} failed on JSON generation: {e}. Attempting fallbacks."
            )
            for provider in self.fallbacks:
                if provider.provider_name == self._current.provider_name:
                    continue
                try:
                    logger.info(f"Trying fallback LLM provider for JSON: {provider.provider_name}")
                    result = await provider.generate_json(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                    old_provider_name = self._current.provider_name
                    self._current = provider
                    logger.info(
                        f"Successfully switched to fallback LLM for JSON: {provider.provider_name} (was: {old_provider_name})"
                    )
                    if self._on_fallback_success:
                        self._on_fallback_success(provider)
                    return result
                except Exception as fe:
                    logger.warning(f"Fallback LLM {provider.provider_name} failed on JSON: {fe}")

            if self._current.provider_name != self.primary.provider_name:
                try:
                    logger.info(f"Retrying primary LLM provider for JSON: {self.primary.provider_name}")
                    result = await self.primary.generate_json(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                    self._current = self.primary
                    logger.info(f"Successfully returned to primary LLM for JSON: {self.primary.provider_name}")
                    return result
                except Exception as pe:
                    logger.warning(f"Primary LLM JSON retry failed: {pe}")

            raise e
