"""Domain exceptions for the RAG layer.

Mirrors the conventions used by :mod:`app.services.exceptions` and
:mod:`app.processing.exceptions`: each failure mode has a dedicated
subclass so callers can react precisely. The HTTP layer translates them
into responses without leaking internal details.
"""
from __future__ import annotations

from uuid import UUID


class RAGError(Exception):
    """Base exception for RAG layer errors."""


class NoRelevantContextError(RAGError):
    """Raised when retrieval returns zero chunks for the given query.

    The endpoint layer translates this into a clean, model-free
    response so the caller still gets a useful answer ("I cannot answer
    this based on the provided documents.").
    """

    def __init__(self, query: str) -> None:
        super().__init__(f"No relevant context found for query: {query!r}")
        self.query = query


class DocumentAccessDeniedError(RAGError):
    """Raised when ``document_id`` belongs to another user (or doesn't exist).

    We surface this as 404 (not 403) on purpose — leaking the existence
    of a document you don't own is itself a privacy violation.
    """

    def __init__(self, document_id: UUID, owner_id: UUID) -> None:
        super().__init__(
            f"Document {document_id} is not accessible to user {owner_id}"
        )
        self.document_id = document_id
        self.owner_id = owner_id


__all__ = [
    "DocumentAccessDeniedError",
    "NoRelevantContextError",
    "RAGError",
]