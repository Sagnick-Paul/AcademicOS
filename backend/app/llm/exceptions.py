"""Domain exceptions for the LLM layer.

Mirrors the conventions used by :mod:`app.processing.exceptions`:
each provider failure mode has a dedicated subclass so callers can
distinguish them without depending on the underlying SDK's types.
"""
from __future__ import annotations


class LLMError(Exception):
    """Base exception for all LLM provider errors."""


class LLMConfigurationError(LLMError):
    """Raised when the provider is misconfigured (missing key, bad model)."""


class LLMProviderUnavailable(LLMError):
    """Raised when the upstream provider cannot be reached (network, 5xx)."""


class LLMResponseInvalid(LLMError):
    """Raised when the provider returns an unparseable or empty response."""


class LLMRequestRejected(LLMError):
    """Raised when the provider rejects the request (auth, quota, safety)."""


__all__ = [
    "LLMError",
    "LLMConfigurationError",
    "LLMProviderUnavailable",
    "LLMResponseInvalid",
    "LLMRequestRejected",
]
