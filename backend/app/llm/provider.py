"""LLM provider factory.

Selects and instantiates the LLM provider based on settings. Mirrors
:func:`app.processing.embeddings.provider.get_embedding_provider`:

* In ``test`` environments the mock provider is used by default — tests
  must never reach out to a real API.
* In all other environments the provider is chosen from ``LLM_PROVIDER``.

The factory reads environment configuration directly from ``os.environ``
on every call so that tests using ``monkeypatch.setenv`` can flip
``ENVIRONMENT`` / ``LLM_PROVIDER`` between cases without having to
mutate the cached :class:`Settings` instance.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import LLMConfigurationError


def _read_env(name: str, default: str = "") -> str:
    """Read an environment variable, honouring monkeypatch mutations."""
    return os.environ.get(name, default)


@lru_cache(maxsize=1)
def get_llm_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
    """Return a singleton LLM provider for the current environment."""
    environment = _read_env("ENVIRONMENT", "development").lower()

    # Tests always default to the mock, regardless of configuration.
    if environment == "test":
        from app.llm.mock_provider import MockLLMProvider

        return MockLLMProvider()

    chosen = (
        provider_name
        or _read_env("LLM_PROVIDER", "gemini")
    ).lower()

    if chosen == "mock":
        from app.llm.mock_provider import MockLLMProvider

        return MockLLMProvider()

    if chosen == "gemini":
        from app.llm.gemini_provider import GeminiLLMProvider

        return GeminiLLMProvider()

    raise LLMConfigurationError(
        f"Unsupported LLM_PROVIDER: {chosen!r}. "
        "Supported providers: 'gemini', 'mock'."
    )


def reset_llm_provider_cache() -> None:
    """Clear the cached provider (used by tests that change settings)."""
    get_llm_provider.cache_clear()


__all__ = ["get_llm_provider", "reset_llm_provider_cache"]