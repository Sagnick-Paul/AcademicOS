"""RAG (Retrieval-Augmented Generation) layer.

Glues together the existing retrieval service, the LLM provider, and the
context builder into a single use case: ``answer_question``. The RAG
service is responsible for:

* invoking retrieval with the right ownership / document filters,
* detecting the empty-context case (so the caller can short-circuit),
* assembling the prompt via :class:`ContextBuilder`,
* calling the LLM, and
* packaging the model's text together with structured citation metadata.

The service raises :class:`LLMError` subclasses on LLM-side failures
and :class:`RetrievalService` exceptions on retrieval-side failures —
the FastAPI boundary translates them into HTTP responses.
"""
from app.rag.context_builder import ContextBuilder
from app.rag.exceptions import (
    DocumentAccessDeniedError,
    NoRelevantContextError,
    RAGError,
)
from app.rag.grounding_prompt import GROUNDING_SYSTEM_PROMPT
from app.rag.service import RAGService

__all__ = [
    "ContextBuilder",
    "DocumentAccessDeniedError",
    "GROUNDING_SYSTEM_PROMPT",
    "NoRelevantContextError",
    "RAGError",
    "RAGService",
]