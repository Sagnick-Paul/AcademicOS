"""Pydantic schemas shared by LLM providers.

The shape is intentionally minimal: a request carries a list of
``LLMMessage`` items (system + user) plus optional generation
parameters; a response carries the model's text plus a token-usage
estimate. Provider-specific extras (safety ratings, finish reason,
etc.) are deliberately not modelled — callers that need them can
subclass.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """A single message in the conversation."""

    role: str = Field(..., description="One of: system, user, assistant.")
    content: str = Field(..., min_length=1)


class LLMRequest(BaseModel):
    """A request to the LLM provider."""

    messages: List[LLMMessage] = Field(..., min_length=1)
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(1024, ge=1, le=8192)


class LLMResponse(BaseModel):
    """A response from the LLM provider."""

    text: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


__all__ = ["LLMMessage", "LLMRequest", "LLMResponse"]
