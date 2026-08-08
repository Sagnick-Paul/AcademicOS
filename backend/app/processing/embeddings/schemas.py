"""Schemas for vector embeddings."""
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EmbeddingVector(BaseModel):
    """A single embedding vector with its metadata and identification."""

    chunk_id: str
    vector: list[float]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: Optional[float] = None

