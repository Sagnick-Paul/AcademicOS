"""Abstract base class for LLM providers.

The interface is intentionally tiny — only what the RAG layer needs.
Streaming, tool calling, multimodal inputs, and structured outputs are
deliberately out of scope; they will be added when the consumer
(agent layer, multimodal search) actually needs them.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.schemas import LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    """Abstract base class for large language model providers."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a model response from a prompt.

        Raises:
            LLMError: any provider-level failure. Subclasses raise the
                more specific :class:`LLMConfigurationError`,
                :class:`LLMProviderUnavailable`, :class:`LLMRequestRejected`,
                or :class:`LLMResponseInvalid` so callers can react
                precisely.
        """
        pass


__all__ = ["BaseLLMProvider"]
