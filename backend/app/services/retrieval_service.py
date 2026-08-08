"""Retrieval service implementing semantic and hybrid search orchestration."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.core.config import settings
from app.processing.embeddings.base import BaseEmbeddingProvider, BaseVectorStore
from app.processing.embeddings.schemas import EmbeddingVector
from app.processing.exceptions import VectorStoreError
from app.schemas.search import RetrievedChunk

logger = logging.getLogger(__name__)


class RetrievalService:
    """Orchestrates semantic and hybrid document chunk retrieval.

    Supported retrieval modes
    -------------------------
    "semantic"
        Dense vector search only — identical to Phase 2 Step 3 behaviour.
        Backward-compatible default.

    "hybrid"
        Dense search  +  keyword search
            ↓                  ↓
          results            results
            └──────── RRF fusion ─────────┘
                           ↓
                     Reranking (normalised linear combination)
                           ↓
                        Top-K
    """

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        vector_store: BaseVectorStore,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    # ------------------------------------------------------------------ #
    #  Public interface                                                    #
    # ------------------------------------------------------------------ #

    async def retrieve(
        self,
        query: str,
        owner_id: UUID,
        limit: int = 5,
        score_threshold: Optional[float] = None,
        document_id: Optional[UUID] = None,
        mode: str = "semantic",
    ) -> List[RetrievedChunk]:
        """Search for relevant document chunks.

        Parameters
        ----------
        query:
            Raw query string from the user.
        owner_id:
            Enforced ownership filter — only chunks belonging to this user
            are ever returned.
        limit:
            Maximum number of results to return.
        score_threshold:
            Optional minimum dense similarity score.  Applied only during
            the dense search phase; does not filter the final reranked list.
        document_id:
            Optional additional filter restricting results to a single
            document.  Applied in **both** dense and keyword search paths.
        mode:
            ``"semantic"`` (default) or ``"hybrid"``.
        """
        if mode == "hybrid":
            return await self._retrieve_hybrid(
                query=query,
                owner_id=owner_id,
                limit=limit,
                score_threshold=score_threshold,
                document_id=document_id,
            )
        return await self._retrieve_semantic(
            query=query,
            owner_id=owner_id,
            limit=limit,
            score_threshold=score_threshold,
            document_id=document_id,
        )

    # ------------------------------------------------------------------ #
    #  Semantic path                                                       #
    # ------------------------------------------------------------------ #

    async def _retrieve_semantic(
        self,
        query: str,
        owner_id: UUID,
        limit: int,
        score_threshold: Optional[float],
        document_id: Optional[UUID],
    ) -> List[RetrievedChunk]:
        """Dense-only retrieval (original Step 3 behaviour)."""
        query_vector = await self.embedding_provider.generate_embedding(query)

        filter_dict: Dict[str, Any] = {"owner_id": str(owner_id)}
        if document_id:
            filter_dict["document_id"] = str(document_id)

        vectors = await self.vector_store.search_vectors(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            filter_dict=filter_dict,
            score_threshold=score_threshold,
        )

        return [self._vec_to_chunk(v) for v in vectors]

    # ------------------------------------------------------------------ #
    #  Hybrid path                                                         #
    # ------------------------------------------------------------------ #

    async def _retrieve_hybrid(
        self,
        query: str,
        owner_id: UUID,
        limit: int,
        score_threshold: Optional[float],
        document_id: Optional[UUID],
    ) -> List[RetrievedChunk]:
        """Hybrid retrieval: dense + keyword → RRF → rerank → top-K."""
        candidate_k = limit * settings.CANDIDATE_MULTIPLIER

        filter_dict: Dict[str, Any] = {"owner_id": str(owner_id)}
        if document_id:
            filter_dict["document_id"] = str(document_id)

        # 1. One embedding call for the whole request.
        query_vector = await self.embedding_provider.generate_embedding(query)

        # 2. Dense search.
        dense_results = await self.vector_store.search_vectors(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=candidate_k,
            filter_dict=filter_dict,
            score_threshold=score_threshold,
        )

        # 3. Keyword search — graceful fallback on failure.
        query_terms = self._tokenize(query)
        keyword_results: List[EmbeddingVector] = []
        if query_terms:
            try:
                keyword_results = await self.vector_store.keyword_search_vectors(
                    collection_name=settings.QDRANT_COLLECTION,
                    query_terms=query_terms,
                    limit=candidate_k,
                    filter_dict=filter_dict,
                )
            except VectorStoreError as exc:
                # Keyword backend unavailable — log and continue with dense only.
                logger.warning(
                    "Keyword search failed in hybrid mode; falling back to dense only. "
                    "Error: %s",
                    exc,
                )

        # 4. Deduplicate by chunk_id (dense score wins on conflict).
        candidates = self._deduplicate(dense_results, keyword_results)

        # 5. RRF fusion.
        rrf_scores = self._rrf_fusion(
            dense_ranked=[v.chunk_id for v in dense_results],
            keyword_ranked=[v.chunk_id for v in keyword_results],
        )

        # 6. Build per-candidate dense-score lookup.
        dense_score_map: Dict[str, float] = {
            v.chunk_id: (v.score if v.score is not None else 0.0)
            for v in dense_results
        }

        # 7. Rerank with normalised signals.
        reranked = self._rerank(candidates, dense_score_map, rrf_scores)

        return reranked[:limit]

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _tokenize(query: str) -> List[str]:
        """Split query into lowercase tokens, removing stopwords and short tokens."""
        _STOPWORDS = {
            "a", "an", "the", "is", "in", "on", "at", "of", "to", "for",
            "and", "or", "but", "not", "with", "by", "from", "as", "it",
            "its", "be", "are", "was", "were", "that", "this", "these",
            "those", "how", "what", "why", "which", "can", "do", "does",
        }
        tokens = re.findall(r"[a-z0-9']+", query.lower())
        return [t for t in tokens if t not in _STOPWORDS and len(t) >= 2]

    @staticmethod
    def _deduplicate(
        dense: List[EmbeddingVector],
        keyword: List[EmbeddingVector],
    ) -> List[EmbeddingVector]:
        """Merge two ranked lists, keeping each chunk_id exactly once.

        Dense result wins when the same chunk appears in both lists
        (preserves the float similarity score).
        """
        seen: Dict[str, EmbeddingVector] = {}
        for vec in dense:
            seen[vec.chunk_id] = vec
        for vec in keyword:
            if vec.chunk_id not in seen:
                seen[vec.chunk_id] = vec
        return list(seen.values())

    @staticmethod
    def _rrf_fusion(
        dense_ranked: List[str],
        keyword_ranked: List[str],
        k: int | None = None,
    ) -> Dict[str, float]:
        """Compute Reciprocal Rank Fusion scores for each chunk_id.

        RRF score = Σ  1 / (k + rank)    for each list the chunk appears in.
        Rank is 1-indexed.

        Parameters
        ----------
        dense_ranked:
            Chunk IDs in dense-result rank order (index 0 = best).
        keyword_ranked:
            Chunk IDs in keyword-result rank order (index 0 = best).
        k:
            RRF smoothing constant.  Defaults to ``settings.RRF_K``.
        """
        rrf_k = k if k is not None else settings.RRF_K
        scores: Dict[str, float] = {}
        for rank, chunk_id in enumerate(dense_ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        for rank, chunk_id in enumerate(keyword_ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
        return scores

    def _rerank(
        self,
        candidates: List[EmbeddingVector],
        dense_score_map: Dict[str, float],
        rrf_scores: Dict[str, float],
    ) -> List[RetrievedChunk]:
        """Final rerank using min-max normalised dense and RRF signals.

        Formula (per candidate)
        -----------------------
            normalised_dense = min_max(dense_score)
            normalised_rrf   = min_max(rrf_score)

            final_score = alpha * normalised_dense + beta * normalised_rrf

        Both signals are normalised **before** weighting so they contribute
        on the same [0, 1] scale regardless of their original magnitudes.
        """
        alpha = settings.RERANK_ALPHA
        beta = settings.RERANK_BETA

        # Gather raw values for normalisation.
        raw_dense = [dense_score_map.get(v.chunk_id, 0.0) for v in candidates]
        raw_rrf = [rrf_scores.get(v.chunk_id, 0.0) for v in candidates]

        norm_dense = self._min_max_normalise(raw_dense)
        norm_rrf = self._min_max_normalise(raw_rrf)

        scored: List[Tuple[float, RetrievedChunk]] = []
        for vec, nd, nr in zip(candidates, norm_dense, norm_rrf):
            final_score = alpha * nd + beta * nr
            chunk = self._vec_to_chunk(vec)
            # Expose the final combined score (not the raw dense score).
            chunk = chunk.model_copy(update={"score": round(final_score, 6)})
            scored.append((final_score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored]

    @staticmethod
    def _min_max_normalise(values: List[float]) -> List[float]:
        """Min-max normalise a list of floats to [0, 1].

        If all values are identical the result is a list of 0.0 (safe
        degenerate case — no signal to differentiate).
        """
        if not values:
            return []
        lo = min(values)
        hi = max(values)
        if hi == lo:
            return [0.0] * len(values)
        span = hi - lo
        return [(v - lo) / span for v in values]

    @staticmethod
    def _vec_to_chunk(vec: EmbeddingVector) -> RetrievedChunk:
        """Map an EmbeddingVector payload to a RetrievedChunk DTO."""
        doc_id_str = vec.metadata.get("document_id")
        doc_uuid = UUID(doc_id_str) if doc_id_str else None

        page_num = vec.metadata.get("page_number")
        chunk_idx = vec.metadata.get("chunk_index", 0)

        inner_metadata = vec.metadata.get("metadata", {})
        text = inner_metadata.get("text", "")

        return RetrievedChunk(
            chunk_id=vec.chunk_id,
            document_id=doc_uuid,
            text=text,
            score=vec.score if vec.score is not None else 0.0,
            page_number=page_num,
            chunk_index=chunk_idx,
            metadata=inner_metadata,
        )
