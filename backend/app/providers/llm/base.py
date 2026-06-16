"""
Abstract base class for LLM providers.
All LLM providers (OpenAI, Claude) must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: str = "text",  # "text" or "json"
    ) -> str:
        """Generate text completion from the LLM.

        Args:
            prompt: User prompt / message.
            system_prompt: System instructions.
            temperature: Creativity control (0.0 - 1.0).
            max_tokens: Maximum response length.
            response_format: Expected format — "text" or "json".

        Returns:
            Generated text string.
        """
        ...

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate a JSON response from the LLM.

        Args:
            prompt: User prompt with JSON schema instructions.
            system_prompt: System instructions.
            temperature: Lower for more deterministic JSON.

        Returns:
            Parsed JSON dictionary.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...
