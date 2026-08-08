"""Schemas for semantic search retrieval."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    """Schema for a semantic search query request."""

    query: str = Field(..., description="The query string to search for.")
    top_k: int = Field(5, ge=1, le=100, description="The maximum number of chunks to return.")
    score_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Minimum similarity score threshold (applied to dense search)."
    )
    document_id: Optional[UUID] = Field(None, description="Optional document ID to restrict the search to.")
    mode: Literal["semantic", "hybrid"] = Field(
        "semantic",
        description=(
            "Retrieval mode. 'semantic' uses dense vector search only (default, backward compatible). "
            "'hybrid' combines dense and keyword search with RRF fusion and reranking."
        ),
    )


    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query string cannot be empty or only whitespace.")
        return v.strip()


class RetrievedChunk(BaseModel):
    """Schema representing a retrieved document chunk with similarity score."""

    chunk_id: str
    document_id: Optional[UUID] = None
    text: str
    score: float
    page_number: Optional[int] = None
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Schema for the search response containing matching chunks."""

    results: List[RetrievedChunk]
