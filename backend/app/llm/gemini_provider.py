"""Gemini LLM provider.

Talks to the Google Gemini REST API (``generativelanguage.googleapis.com``)
over ``httpx``. We deliberately avoid the ``google-generativeai`` SDK to
keep the project's dependency footprint minimal — the SDK adds a fair
amount of surface area we don't need, and the REST call is small.

The provider is configured via three settings:

* ``LLM_PROVIDER``  — must be ``"gemini"`` to select this provider.
* ``GEMINI_API_KEY`` — API key used in the ``?key=`` query parameter.
* ``LLM_MODEL``     — the model identifier (default: ``gemini-1.5-flash``).

All endpoints raise :class:`LLMError` subclasses; never raw
``httpx``/``JSON`` exceptions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMProviderUnavailable,
    LLMRequestRejected,
    LLMResponseInvalid,
)
from app.llm.schemas import LLMMessage, LLMRequest, LLMResponse

logger = get_logger(__name__)


class GeminiLLMProvider(BaseLLMProvider):
    """LLM provider backed by Google's Gemini REST API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.LLM_MODEL
        self.timeout_seconds = timeout_seconds
        if not self.api_key:
            raise LLMConfigurationError(
                "GEMINI_API_KEY is not configured; cannot use GeminiLLMProvider."
            )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Call Gemini's ``generateContent`` endpoint.

        Maps ``LLMRequest.messages`` to Gemini's ``systemInstruction`` +
        ``contents`` shape: any message with role ``system`` becomes the
        system instruction, everything else becomes user/model turns.
        """
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"
        body = self._build_body(request)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(
                    url,
                    params={"key": self.api_key},
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderUnavailable(
                f"Gemini request timed out after {self.timeout_seconds}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderUnavailable(f"Gemini request failed: {exc}") from exc

        if resp.status_code == 401 or resp.status_code == 403:
            raise LLMRequestRejected(
                f"Gemini rejected the request (auth): {resp.status_code}"
            )
        if resp.status_code == 429:
            raise LLMRequestRejected("Gemini rate-limited the request (429)")
        if resp.status_code >= 500:
            raise LLMProviderUnavailable(
                f"Gemini server error: {resp.status_code} {resp.text[:200]}"
            )
        if resp.status_code >= 400:
            raise LLMRequestRejected(
                f"Gemini request rejected ({resp.status_code}): {resp.text[:200]}"
            )

        try:
            payload = resp.json()
        except Exception as exc:
            raise LLMResponseInvalid(f"Gemini returned non-JSON response: {exc}") from exc

        text, usage = self._extract_text_and_usage(payload)
        if not text:
            raise LLMResponseInvalid("Gemini returned an empty completion.")

        logger.info(
            "llm.gemini.generate model=%s prompt_tokens=%s completion_tokens=%s",
            self.model,
            usage.get("prompt"),
            usage.get("completion"),
        )
        return LLMResponse(
            text=text,
            model=self.model,
            prompt_tokens=usage.get("prompt"),
            completion_tokens=usage.get("completion"),
        )

    # ----- helpers -----

    @staticmethod
    def _build_body(request: LLMRequest) -> Dict[str, Any]:
        """Convert :class:`LLMRequest` to a Gemini request body."""
        system_parts: List[Dict[str, Any]] = []
        contents: List[Dict[str, Any]] = []
        for msg in request.messages:
            if msg.role == "system":
                system_parts.append({"text": msg.content})
            elif msg.role == "assistant":
                contents.append(
                    {"role": "model", "parts": [{"text": msg.content}]}
                )
            else:
                # Treat anything that isn't system/assistant as a user turn.
                contents.append(
                    {"role": "user", "parts": [{"text": msg.content}]}
                )

        generation_config: Dict[str, Any] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_output_tokens,
        }
        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system_parts:
            body["systemInstruction"] = {"parts": system_parts}
        return body

    @staticmethod
    def _extract_text_and_usage(payload: Dict[str, Any]) -> tuple[str, Dict[str, Optional[int]]]:
        """Pull the generated text and token usage out of a Gemini response.

        Returns ``("", {"prompt": None, "completion": None})`` when the
        response is missing the expected fields.
        """
        text = ""
        candidates = payload.get("candidates") or []
        if candidates:
            parts = (
                candidates[0].get("content", {}).get("parts", []) or []
            )
            chunks = [
                p.get("text", "")
                for p in parts
                if isinstance(p, dict) and p.get("text")
            ]
            text = "".join(chunks).strip()
        usage_meta = payload.get("usageMetadata") or {}
        usage = {
            "prompt": usage_meta.get("promptTokenCount"),
            "completion": usage_meta.get("candidatesTokenCount"),
        }
        return text, usage


__all__ = ["GeminiLLMProvider"]
