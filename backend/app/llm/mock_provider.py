"""Mock LLM provider for tests and local development.

Returns a deterministic, non-empty response whose content references the
number of source chunks passed in the prompt. This lets tests assert on
both:

* the prompt construction (context size, source headers), and
* the high-level "did the model see any sources?" question.

The mock is selected automatically when ``LLM_PROVIDER == "mock"`` or
when ``ENVIRONMENT == "test"`` (handled by the factory).
"""
from __future__ import annotations

from typing import Optional

from app.llm.base import BaseLLMProvider
from app.llm.schemas import LLMRequest, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """Deterministic LLM provider used in tests.

    The generated text includes a ``SOURCES_USED=<n>`` marker so tests
    can verify how many context chunks the caller fed into the prompt
    without parsing natural language.
    """

    def __init__(
        self,
        model: str = "mock-llm",
        response_text: Optional[str] = None,
    ) -> None:
        self.model = model
        self.response_text = response_text

    async def generate(self, request: LLMRequest) -> LLMResponse:
        # Pull the user message (last user turn). The RAG layer puts the
        # full prompt there, so the source count is observable.
        user_messages = [m for m in request.messages if m.role == "user"]
        user_text = user_messages[-1].content if user_messages else ""

        source_count = user_text.count("[SOURCE ")
        if self.response_text is not None:
            text = self.response_text
        else:
            text = (
                "This is a mock LLM response. "
                f"SOURCES_USED={source_count} "
                f"temperature={request.temperature} "
                f"max_tokens={request.max_output_tokens}"
            )

        return LLMResponse(
            text=text,
            model=self.model,
            prompt_tokens=None,
            completion_tokens=None,
        )


__all__ = ["MockLLMProvider"]
