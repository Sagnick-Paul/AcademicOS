"""Qdrant vector store integration implementation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from app.processing.exceptions import VectorStoreError
from app.processing.embeddings.base import BaseVectorStore
from app.processing.embeddings.schemas import EmbeddingVector


class QdrantVectorStore(BaseVectorStore):
    """Qdrant implementation of the BaseVectorStore."""

    def __init__(self, client: QdrantClient | None = None) -> None:
        """Initialize the Qdrant client.

        If in a test environment and no client is provided, falls back to an
        in-memory Qdrant client.
        """
        if client is not None:
            self.client = client
        elif settings.ENVIRONMENT == "test":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
            )

    async def create_collection(self, collection_name: str, vector_size: int) -> None:
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
        except Exception as exc:
            raise VectorStoreError(f"Failed to create collection {collection_name}: {exc}") from exc

    async def upsert_vectors(self, collection_name: str, vectors: List[EmbeddingVector]) -> None:
        if not vectors:
            return
        try:
            points = []
            for vec in vectors:
                points.append(
                    models.PointStruct(
                        id=vec.chunk_id,
                        vector=vec.vector,
                        payload=vec.metadata,
                    )
                )
            self.client.upsert(
                collection_name=collection_name,
                points=points,
            )
        except Exception as exc:
            raise VectorStoreError(f"Failed to upsert vectors into {collection_name}: {exc}") from exc

    async def delete_vectors(self, collection_name: str, filter_dict: Dict[str, Any]) -> None:
        try:
            conditions = []
            for key, val in filter_dict.items():
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=str(val)),
                    )
                )
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=conditions)
                ),
            )
        except Exception as exc:
            raise VectorStoreError(f"Failed to delete vectors from {collection_name}: {exc}") from exc

    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[EmbeddingVector]:
        try:
            # If the collection has never been created (e.g. no documents indexed yet),
            # return an empty result set rather than propagating a Qdrant exception.
            collections = self.client.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                return []

            conditions = []
            if filter_dict:
                for key, val in filter_dict.items():
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=str(val)),
                        )
                    )
            q_filter = models.Filter(must=conditions) if conditions else None

            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=q_filter,
                with_vectors=True,
                score_threshold=score_threshold,
            )
            return [
                EmbeddingVector(
                    chunk_id=str(point.id),
                    vector=point.vector if isinstance(point.vector, list) else [],
                    metadata=point.payload or {},
                    score=point.score,
                )
                for point in results
            ]
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"Failed to search vectors in {collection_name}: {exc}") from exc

    def _build_exact_filter(self, filter_dict: Optional[Dict[str, Any]]) -> List[models.FieldCondition]:
        """Build a list of exact-match FieldConditions from a plain dict."""
        if not filter_dict:
            return []
        return [
            models.FieldCondition(key=key, match=models.MatchValue(value=str(val)))
            for key, val in filter_dict.items()
        ]

    async def keyword_search_vectors(
        self,
        collection_name: str,
        query_terms: List[str],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[EmbeddingVector]:
        """Search for chunks containing any of query_terms in their payload text.

        Results are ordered deterministically:
        1. Descending by number of distinct query_terms found in the chunk text
           (case-insensitive substring match).
        2. Ascending by chunk_id as a stable tie-breaker.

        The ``score`` field carries the raw term-match count so the caller can
        apply normalisation before weighting.

        Raises:
            VectorStoreError: if the underlying Qdrant scroll fails.
        """
        if not query_terms:
            return []
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                return []

            base_conditions = self._build_exact_filter(filter_dict)

            # Fetch candidates matching ANY query term via OR over MatchText filters.
            # Qdrant scroll + MatchText gives us the matched set; we score them
            # ourselves to achieve a deterministic, reproducible ordering.
            should_conditions = [
                models.FieldCondition(
                    key="metadata.text",
                    match=models.MatchText(text=term),
                )
                for term in query_terms
                if term.strip()
            ]
            if not should_conditions:
                return []

            scroll_filter = models.Filter(
                must=base_conditions,
                should=should_conditions,
            )

            all_points, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=limit * 5,  # over-fetch; we re-rank and trim to limit
                with_payload=True,
                with_vectors=False,
            )

            # Score each point by how many query terms it contains (case-insensitive).
            terms_lower = [t.lower() for t in query_terms if t.strip()]
            scored: list[tuple[int, str, Any]] = []  # (match_count, chunk_id, point)
            for point in all_points:
                payload = point.payload or {}
                text = (payload.get("metadata") or {}).get("text", "").lower()
                match_count = sum(1 for t in terms_lower if t in text)
                scored.append((match_count, str(point.id), point))

            # Sort: most matches first, then chunk_id ascending for tie-breaking.
            scored.sort(key=lambda x: (-x[0], x[1]))
            scored = scored[:limit]

            return [
                EmbeddingVector(
                    chunk_id=str(point.id),
                    vector=[],  # not fetched; not needed for keyword path
                    metadata=point.payload or {},
                    score=float(match_count),  # raw match count; caller normalises
                )
                for match_count, _, point in scored
            ]
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(
                f"Failed keyword search in {collection_name}: {exc}"
            ) from exc
