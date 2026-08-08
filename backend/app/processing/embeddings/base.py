"""Base interfaces for embedding providers and vector stores."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.processing.embeddings.schemas import EmbeddingVector


class BaseEmbeddingProvider(ABC):
    """Abstract base class for generating text embeddings."""

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.

        Raises:
            EmbeddingGenerationFailed: if generation fails.
        """
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a single embedding for a piece of text.

        Raises:
            EmbeddingGenerationFailed: if generation fails.
        """
        pass


class BaseVectorStore(ABC):
    """Abstract base class for vector store operations."""

    @abstractmethod
    async def create_collection(self, collection_name: str, vector_size: int) -> None:
        """Create a vector collection if it does not exist.

        Raises:
            VectorStoreError: if collection creation fails.
        """
        pass

    @abstractmethod
    async def upsert_vectors(self, collection_name: str, vectors: List[EmbeddingVector]) -> None:
        """Upsert a list of embedding vectors into the specified collection.

        Raises:
            VectorStoreError: if insertion fails.
        """
        pass

    @abstractmethod
    async def delete_vectors(self, collection_name: str, filter_dict: Dict[str, Any]) -> None:
        """Delete vectors from the collection matching the filter metadata.

        Raises:
            VectorStoreError: if deletion fails.
        """
        pass

    @abstractmethod
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[EmbeddingVector]:
        """Search for similar vectors in the collection.

        Raises:
            VectorStoreError: if search fails.
        """
        pass

    @abstractmethod
    async def keyword_search_vectors(
        self,
        collection_name: str,
        query_terms: List[str],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[EmbeddingVector]:
        """Search for chunks whose payload text contains any of the query_terms.

        Results are returned with a deterministic ordering:
        1. Descending by number of query_terms matched in the chunk text.
        2. Ascending by chunk_id as a stable tie-breaker.

        ``score`` on returned ``EmbeddingVector`` objects carries the raw
        term-match count (not a similarity score).  The caller is responsible
        for normalisation before combining with dense scores.

        Raises:
            VectorStoreError: if the underlying keyword search fails.
        """
        pass

