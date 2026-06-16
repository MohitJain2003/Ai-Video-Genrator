"""
Unit tests for the FallbackLLMProvider and dynamic provider failover.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
import pytest

from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.fallback import FallbackLLMProvider
from app.pipeline.orchestrator import update_env_default_llm, _get_llm
from app.config import get_settings, LLMProvider


class DummyWorkingProvider(BaseLLMProvider):
    def __init__(self, name: str, value: str = "success_response"):
        self._name = name
        self.value = value

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: str = "text",
    ) -> str:
        return self.value

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        return {"result": self.value}


class DummyFailingProvider(BaseLLMProvider):
    def __init__(self, name: str, exception: Exception):
        self._name = name
        self.exception = exception

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: str = "text",
    ) -> str:
        raise self.exception

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        raise self.exception


@pytest.mark.asyncio
async def test_fallback_success():
    """Verify that FallbackLLMProvider switches to a fallback when primary fails."""
    primary = DummyFailingProvider("FailingPrimary", ValueError("API limit reached"))
    fallback = DummyWorkingProvider("WorkingFallback", "worked!")
    
    success_called = []
    def on_success(provider):
        success_called.append(provider)

    provider = FallbackLLMProvider(
        primary=primary,
        fallbacks=[fallback],
        on_fallback_success=on_success,
    )

    # 1. Test generate text fallback
    res = await provider.generate("test prompt")
    assert res == "worked!"
    assert provider.provider_name == "WorkingFallback"
    assert len(success_called) == 1
    assert success_called[0].provider_name == "WorkingFallback"

    # 2. Test subsequent call goes directly to current working provider
    res_subsequent = await provider.generate("another prompt")
    assert res_subsequent == "worked!"
    # on_success callback only called when switching, so still 1
    assert len(success_called) == 1


@pytest.mark.asyncio
async def test_fallback_json_success():
    """Verify that generate_json also supports fallback."""
    primary = DummyFailingProvider("FailingPrimary", ValueError("Rate limit"))
    fallback = DummyWorkingProvider("WorkingFallback", "json_worked")
    
    provider = FallbackLLMProvider(
        primary=primary,
        fallbacks=[fallback],
    )

    res = await provider.generate_json("test prompt")
    assert res == {"result": "json_worked"}
    assert provider.provider_name == "WorkingFallback"


def test_update_env_default_llm():
    """Verify that update_env_default_llm updates the correct line in the file."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".env", delete=False) as f:
        f.write("SOME_VAR=123\nDEFAULT_LLM_PROVIDER=groq\nANOTHER_VAR=456\n")
        env_path = Path(f.name)

    try:
        # We patch the path list inside update_env_default_llm by modifying its env_paths
        # or we can simply run it and let it find the file since we will patch Path.exists
        import app.pipeline.orchestrator
        original_env_paths = app.pipeline.orchestrator.update_env_default_llm.__globals__.get("Path")
        
        # Call it with custom path checking
        # To make it clean, let's temporarily mock env_paths detection
        # Since env_paths has Path(".env"), Path("backend/.env") etc., we can mock the search inside update_env_default_llm
        # Let's inspect the code of update_env_default_llm: it iterates over hardcoded env_paths.
        # Let's check how we can redirect it to our temp file.
        # We can temporarily patch the env_paths list.
        # However, Python module attributes are mutable, but env_paths is defined inside the function.
        # Let's mock Path inside app.pipeline.orchestrator:
        import sys
        from unittest.mock import patch

        with patch("app.pipeline.orchestrator.Path") as mock_path:
            # mock_path instances must say they exist if they match one of the searches,
            # and return the content of our temp file on read/write.
            mock_inst = mock_path.return_value
            mock_path.side_effect = lambda *args: Path(env_path) if args and ".env" in str(args[0]) else Path(*args)
            
            update_env_default_llm("sambanova")
            
        content = env_path.read_text(encoding="utf-8")
        assert "DEFAULT_LLM_PROVIDER=sambanova" in content
        assert "SOME_VAR=123" in content
        assert "ANOTHER_VAR=456" in content
    finally:
        env_path.unlink()
