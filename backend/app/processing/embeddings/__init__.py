"""Embeddings and vector storage foundation module."""
from __future__ import annotations

from app.processing.embeddings.base import BaseEmbeddingProvider, BaseVectorStore
from app.processing.embeddings.provider import SentenceTransformerEmbeddingProvider, get_embedding_provider
from app.processing.embeddings.qdrant import QdrantVectorStore
from app.processing.embeddings.schemas import EmbeddingVector

__all__ = [
    "BaseEmbeddingProvider",
    "BaseVectorStore",
    "EmbeddingVector",
    "SentenceTransformerEmbeddingProvider",
    "QdrantVectorStore",
    "get_embedding_provider",
]

