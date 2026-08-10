"""Tests for LLM providers and the provider factory."""
from __future__ import annotations

import pytest

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMError,
)
from app.llm.mock_provider import MockLLMProvider
from app.llm.provider import (
    get_llm_provider,
    reset_llm_provider_cache,
)
from app.llm.schemas import LLMMessage, LLMRequest, LLMResponse


@pytest.fixture(autouse=True)
def _reset_factory_cache():
    """Reset the LLM provider cache before AND after each test so the
    ``lru_cache`` cannot leak state from a previous test."""
    reset_llm_provider_cache()
    yield
    reset_llm_provider_cache()


# ─── Schema validation ────────────────────────────────────────────────────────


def test_llm_request_validates_min_messages() -> None:
    """LLMRequest requires at least one message."""
    with pytest.raises(ValueError):
        LLMRequest(messages=[])


def test_llm_request_temperature_bounds() -> None:
    """Temperature must be within [0, 2]."""
    with pytest.raises(ValueError):
        LLMRequest(
            messages=[LLMMessage(role="user", content="hi")],
            temperature=-0.1,
        )
    with pytest.raises(ValueError):
        LLMRequest(
            messages=[LLMMessage(role="user", content="hi")],
            temperature=2.5,
        )


def test_llm_request_max_tokens_bounds() -> None:
    """max_output_tokens must be within [1, 8192]."""
    with pytest.raises(ValueError):
        LLMRequest(
            messages=[LLMMessage(role="user", content="hi")],
            max_output_tokens=0,
        )


# ─── Mock provider ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_mock_provider_returns_text() -> None:
    """Mock provider always returns a non-empty response."""
    p = MockLLMProvider()
    req = LLMRequest(
        messages=[LLMMessage(role="user", content="hello")],
    )
    resp = await p.generate(req)
    assert isinstance(resp, LLMResponse)
    assert resp.text


@pytest.mark.anyio
async def test_mock_provider_counts_sources_in_prompt() -> None:
    """Mock provider reports how many [SOURCE n] headers were given."""
    p = MockLLMProvider()
    req = LLMRequest(
        messages=[
            LLMMessage(
                role="user",
                content=(
                    "[SOURCE 1]\nfoo\n\n"
                    "[SOURCE 2]\nbar\n\n"
                    "[SOURCE 3]\nbaz"
                ),
            )
        ],
    )
    resp = await p.generate(req)
    assert "SOURCES_USED=3" in resp.text


@pytest.mark.anyio
async def test_mock_provider_custom_response() -> None:
    """Response_text override is respected."""
    p = MockLLMProvider(response_text="custom answer")
    resp = await p.generate(
        LLMRequest(messages=[LLMMessage(role="user", content="x")])
    )
    assert resp.text == "custom answer"


def test_mock_provider_is_base_llm_provider() -> None:
    """Mock provider satisfies the abstract interface contract."""
    p = MockLLMProvider()
    assert isinstance(p, BaseLLMProvider)


# ─── Provider factory ─────────────────────────────────────────────────────────


def test_factory_returns_mock_when_provider_is_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit 'mock' selection returns MockLLMProvider."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    p = get_llm_provider()
    assert isinstance(p, MockLLMProvider)


def test_factory_returns_mock_in_test_environment() -> None:
    """ENVIRONMENT=test always uses the mock provider."""
    # conftest already sets ENVIRONMENT=test; this guards the rule.
    p = get_llm_provider()
    assert isinstance(p, MockLLMProvider)


def test_factory_rejects_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown LLM_PROVIDER raises LLMConfigurationError."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "openai-rodeo")
    with pytest.raises(LLMConfigurationError, match="Unsupported LLM_PROVIDER"):
        get_llm_provider()


def test_factory_gemini_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selecting Gemini without GEMINI_API_KEY raises LLMConfigurationError."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
        get_llm_provider()


def test_factory_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_llm_provider returns the same instance within one process."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    first = get_llm_provider()
    second = get_llm_provider()
    assert first is second


def test_reset_clears_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """reset_llm_provider_cache forces a fresh instance on next call."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    first = get_llm_provider()
    reset_llm_provider_cache()
    second = get_llm_provider()
    assert first is not second
