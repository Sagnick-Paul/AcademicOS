"""LLM provider integrations.

Wrappers around large language model APIs (Gemini, OpenAI, ...) behind a
single, narrow interface so the RAG layer stays decoupled from the
underlying SDK. The pattern mirrors :mod:`app.processing.embeddings`:

    BaseLLMProvider
        │
        ├── GeminiLLMProvider
        └── MockLLMProvider
"""
from __future__ import annotations

from app.llm.base import BaseLLMProvider
from app.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from app.llm.provider import get_llm_provider

__all__ = [
    "BaseLLMProvider",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "get_llm_provider",
]
