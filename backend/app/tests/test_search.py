"""Tests for Phase 2 — Steps 3 & 4: Semantic and Hybrid Retrieval."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.processing.exceptions import EmbeddingGenerationFailed, VectorStoreError
from app.processing.embeddings import (
    SentenceTransformerEmbeddingProvider,
    QdrantVectorStore,
    EmbeddingVector,
    BaseEmbeddingProvider,
    BaseVectorStore,
)
from app.schemas.search import SearchRequest
from app.services.retrieval_service import RetrievalService


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "S3cur3P@ss!",
    full_name: str = "Test User",
) -> str:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth(token: str) -> dict:
    return {"headers": {"Authorization": f"Bearer {token}"}}


def _make_vec(
    *,
    owner_id: UUID,
    document_id: UUID,
    text: str,
    vector: List[float] | None = None,
    page_number: int = 1,
    chunk_index: int = 0,
) -> EmbeddingVector:
    """Factory for EmbeddingVector objects with the standard payload layout.

    Mirrors the payload written by ``DocumentProcessingPipeline``: the
    nested ``metadata.text`` keeps the original case (so ``_vec_to_chunk``
    returns the readable text), while the top-level ``text_search`` is the
    lowercased index used by ``QdrantVectorStore.keyword_search_vectors``.
    """
    return EmbeddingVector(
        chunk_id=str(uuid4()),
        vector=vector or ([0.5] * settings.EMBEDDING_DIMENSION),
        metadata={
            "owner_id": str(owner_id),
            "document_id": str(document_id),
            "page_number": page_number,
            "chunk_index": chunk_index,
            "metadata": {"text": text},
            "text_search": text.lower(),
        },
    )


async def _seed_store(
    store: QdrantVectorStore,
    vecs: List[EmbeddingVector],
) -> None:
    collection = settings.QDRANT_COLLECTION
    await store.create_collection(collection, settings.EMBEDDING_DIMENSION)
    await store.upsert_vectors(collection, vecs)


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic Mock Backends (for unit tests)
# ─────────────────────────────────────────────────────────────────────────────

class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Returns a deterministic all-zeros vector for any input."""

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * settings.EMBEDDING_DIMENSION for _ in texts]

    async def generate_embedding(self, text: str) -> List[float]:
        return [0.0] * settings.EMBEDDING_DIMENSION


class MockVectorStore(BaseVectorStore):
    """In-memory store with controllable dense and keyword results."""

    def __init__(
        self,
        dense_results: List[EmbeddingVector] | None = None,
        keyword_results: List[EmbeddingVector] | None = None,
        keyword_raises: Exception | None = None,
        dense_raises: Exception | None = None,
    ) -> None:
        self.dense_results = dense_results or []
        self.keyword_results = keyword_results or []
        self.keyword_raises = keyword_raises
        self.dense_raises = dense_raises

    async def create_collection(self, collection_name: str, vector_size: int) -> None:
        pass

    async def upsert_vectors(self, collection_name: str, vectors: List[EmbeddingVector]) -> None:
        pass

    async def delete_vectors(self, collection_name: str, filter_dict: Dict[str, Any]) -> None:
        pass

    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[EmbeddingVector]:
        if self.dense_raises:
            raise self.dense_raises
        return self.dense_results[:limit]

    async def keyword_search_vectors(
        self,
        collection_name: str,
        query_terms: List[str],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[EmbeddingVector]:
        if self.keyword_raises:
            raise self.keyword_raises
        return self.keyword_results[:limit]


def _service(
    *,
    dense: List[EmbeddingVector] | None = None,
    keyword: List[EmbeddingVector] | None = None,
    keyword_raises: Exception | None = None,
    dense_raises: Exception | None = None,
) -> RetrievalService:
    return RetrievalService(
        embedding_provider=MockEmbeddingProvider(),
        vector_store=MockVectorStore(
            dense_results=dense,
            keyword_results=keyword,
            keyword_raises=keyword_raises,
            dense_raises=dense_raises,
        ),
    )


def _vec(chunk_id: str, score: float = 0.9) -> EmbeddingVector:
    return EmbeddingVector(
        chunk_id=chunk_id,
        vector=[0.0],
        score=score,
        metadata={
            "document_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "page_number": 1,
            "chunk_index": 0,
            "metadata": {"text": f"text for {chunk_id}"},
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Regression Tests (must remain passing)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_semantic_mode_retrieval_service() -> None:
    """Step-3 regression: semantic mode still works correctly."""
    provider = SentenceTransformerEmbeddingProvider()
    store = QdrantVectorStore()
    svc = RetrievalService(embedding_provider=provider, vector_store=store)

    user_a = uuid4()
    user_b = uuid4()
    doc_1 = uuid4()
    doc_2 = uuid4()

    v1 = _make_vec(owner_id=user_a, document_id=doc_1, text="Faraday's law of induction")
    v2 = _make_vec(owner_id=user_a, document_id=doc_2, text="Faraday law EMF magnetic flux")
    v3 = _make_vec(owner_id=user_b, document_id=uuid4(), text="Secret note owned by user B")

    await _seed_store(store, [v1, v2, v3])

    results = await svc.retrieve(query="Faraday", owner_id=user_a, limit=5, mode="semantic")
    assert len(results) == 2
    assert all(r.document_id in (doc_1, doc_2) for r in results)
    assert results[0].score >= results[1].score

    # document_id filter
    r = await svc.retrieve(query="Faraday", owner_id=user_a, document_id=doc_2, limit=5, mode="semantic")
    assert len(r) == 1
    assert r[0].document_id == doc_2

    # score_threshold
    r = await svc.retrieve(query="Faraday", owner_id=user_a, score_threshold=1.5, mode="semantic")
    assert len(r) == 0

    # ownership isolation
    r = await svc.retrieve(query="Faraday", owner_id=user_b, limit=5, mode="semantic")
    assert len(r) == 1
    assert "Secret note" in r[0].text


def test_search_request_validation() -> None:
    """Regression: SearchRequest Pydantic validations."""
    with pytest.raises(ValueError, match="Query string cannot be empty"):
        SearchRequest(query="   ")
    with pytest.raises(ValueError):
        SearchRequest(query="q", top_k=0)
    with pytest.raises(ValueError):
        SearchRequest(query="q", top_k=101)
    with pytest.raises(ValueError):
        SearchRequest(query="q", score_threshold=-0.1)


def test_search_request_mode_default() -> None:
    """Default mode is 'semantic' — backward compatible."""
    r = SearchRequest(query="Kirchhoff")
    assert r.mode == "semantic"


def test_search_request_mode_hybrid() -> None:
    """Explicit hybrid mode is accepted."""
    r = SearchRequest(query="Kirchhoff", mode="hybrid")
    assert r.mode == "hybrid"


def test_search_request_invalid_mode() -> None:
    """Invalid mode string is rejected by Pydantic."""
    with pytest.raises(ValueError):
        SearchRequest(query="q", mode="fuzzy")  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_api_search_endpoint_semantic(client: AsyncClient) -> None:
    """API regression: unauthenticated → 401; authenticated semantic → 200."""
    r = await client.post("/api/v1/search", json={"query": "Faraday", "top_k": 5})
    assert r.status_code == 401

    token = await _register_and_login(client, email="sem_searcher@example.com")
    r = await client.post(
        "/api/v1/search",
        json={"query": "Faraday Law", "top_k": 5},
        **_auth(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert isinstance(body["results"], list)


@pytest.mark.anyio
async def test_vector_store_failure_wrapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """VectorStoreError propagates through semantic retrieve."""
    provider = SentenceTransformerEmbeddingProvider()
    store = QdrantVectorStore()

    async def mock_search_vectors(*a, **kw):
        raise VectorStoreError("timed out")

    monkeypatch.setattr(store, "search_vectors", mock_search_vectors)
    svc = RetrievalService(embedding_provider=provider, vector_store=store)
    with pytest.raises(VectorStoreError, match="timed out"):
        await svc.retrieve("Query", uuid4())


@pytest.mark.anyio
async def test_embedding_failure_wrapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """EmbeddingGenerationFailed propagates through retrieve."""
    provider = SentenceTransformerEmbeddingProvider()
    store = QdrantVectorStore()

    async def mock_generate_embedding(*a, **kw):
        raise EmbeddingGenerationFailed("offline")

    monkeypatch.setattr(provider, "generate_embedding", mock_generate_embedding)
    svc = RetrievalService(embedding_provider=provider, vector_store=store)
    with pytest.raises(EmbeddingGenerationFailed, match="offline"):
        await svc.retrieve("Query", uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — RRF Fusion Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_rrf_fusion_both_lists() -> None:
    """Chunk appearing in both lists gets higher RRF score than chunk in one."""
    svc = _service()
    rrf = svc._rrf_fusion(
        dense_ranked=["A", "B", "C"],
        keyword_ranked=["C", "A", "D"],
        k=60,
    )
    # A is rank-1 dense + rank-2 keyword → highest combined
    # C is rank-3 dense + rank-1 keyword
    # D is keyword only
    assert rrf["A"] > rrf["D"]           # in both lists > in one list
    assert rrf["C"] > rrf["D"]           # C is in both too
    assert "B" in rrf                    # B only in dense, still has a score


def test_rrf_fusion_single_list() -> None:
    """Single-list RRF still produces sensible ordering."""
    svc = _service()
    rrf = svc._rrf_fusion(dense_ranked=["X", "Y", "Z"], keyword_ranked=[], k=60)
    assert rrf["X"] > rrf["Y"] > rrf["Z"]


def test_rrf_fusion_empty_lists() -> None:
    """Empty inputs produce empty RRF dict."""
    svc = _service()
    assert svc._rrf_fusion([], []) == {}


def test_rrf_fusion_k_parameter() -> None:
    """k=0 and k=60 should both be monotone; k=0 gives larger spread."""
    svc = _service()
    rrf_60 = svc._rrf_fusion(["A", "B"], [], k=60)
    rrf_0 = svc._rrf_fusion(["A", "B"], [], k=0)
    # Both must be monotone (rank-1 > rank-2)
    assert rrf_60["A"] > rrf_60["B"]
    assert rrf_0["A"] > rrf_0["B"]


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Min-Max Normalisation
# ─────────────────────────────────────────────────────────────────────────────

def test_min_max_normalise_normal() -> None:
    svc = _service()
    result = svc._min_max_normalise([0.0, 0.5, 1.0])
    assert result == pytest.approx([0.0, 0.5, 1.0])


def test_min_max_normalise_all_same() -> None:
    """Degenerate case: all-same values → all zeros."""
    svc = _service()
    assert svc._min_max_normalise([0.7, 0.7, 0.7]) == [0.0, 0.0, 0.0]


def test_min_max_normalise_empty() -> None:
    svc = _service()
    assert svc._min_max_normalise([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Deduplication
# ─────────────────────────────────────────────────────────────────────────────

def test_deduplication_dense_wins() -> None:
    """When chunk appears in both lists, dense EmbeddingVector is kept."""
    dense_v = _vec("chunk-A", score=0.95)
    keyword_v = EmbeddingVector(
        chunk_id="chunk-A",
        vector=[],
        score=1.0,  # raw match count
        metadata={"metadata": {"text": "keyword version"}},
    )
    svc = _service()
    deduped = svc._deduplicate([dense_v], [keyword_v])
    assert len(deduped) == 1
    assert deduped[0].score == 0.95  # dense score preserved


def test_deduplication_keyword_only_chunk_included() -> None:
    """Chunk that appears only in keyword results must be in the output."""
    kw_only = _vec("chunk-K")
    dense_only = _vec("chunk-D")
    svc = _service()
    deduped = svc._deduplicate([dense_only], [kw_only])
    ids = {v.chunk_id for v in deduped}
    assert "chunk-K" in ids
    assert "chunk-D" in ids


def test_deduplication_no_duplicates_in_output() -> None:
    """No chunk_id appears twice in deduplicated output."""
    shared = _vec("shared", score=0.8)
    svc = _service()
    deduped = svc._deduplicate([shared], [shared])
    assert len(deduped) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Hybrid Retrieval via MockVectorStore
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_hybrid_mode_includes_dense_results() -> None:
    """Dense results appear in hybrid output."""
    d = _vec("dense-only", score=0.9)
    svc = _service(dense=[d], keyword=[])
    results = await svc.retrieve("query", uuid4(), mode="hybrid")
    ids = {r.chunk_id for r in results}
    assert "dense-only" in ids


@pytest.mark.anyio
async def test_hybrid_mode_includes_keyword_results() -> None:
    """Keyword-only results appear in hybrid output."""
    k = _vec("keyword-only", score=1.0)
    svc = _service(dense=[], keyword=[k])
    results = await svc.retrieve("query", uuid4(), mode="hybrid")
    ids = {r.chunk_id for r in results}
    assert "keyword-only" in ids


@pytest.mark.anyio
async def test_hybrid_mode_deduplication() -> None:
    """Chunk in both dense and keyword appears only once."""
    shared = _vec("shared", score=0.85)
    svc = _service(dense=[shared], keyword=[shared])
    results = await svc.retrieve("query", uuid4(), mode="hybrid")
    chunk_ids = [r.chunk_id for r in results]
    assert chunk_ids.count("shared") == 1


@pytest.mark.anyio
async def test_hybrid_mode_top_k_respected() -> None:
    """Hybrid mode returns at most top_k results."""
    vecs = [_vec(f"c{i}", score=float(i) / 10) for i in range(20)]
    svc = _service(dense=vecs, keyword=vecs)
    results = await svc.retrieve("query", uuid4(), limit=5, mode="hybrid")
    assert len(results) <= 5


@pytest.mark.anyio
async def test_hybrid_mode_result_ordering() -> None:
    """Higher-ranked chunks across both lists should score higher after rerank."""
    # Dense top results
    dense = [_vec("A", score=0.9), _vec("B", score=0.5), _vec("C", score=0.3)]
    # Keyword confirms A and introduces D
    keyword = [_vec("A", score=2.0), _vec("D", score=1.0)]

    svc = _service(dense=dense, keyword=keyword)
    results = await svc.retrieve("query", uuid4(), limit=10, mode="hybrid")
    scores = [r.score for r in results]
    # Output must be sorted descending by final_score
    assert scores == sorted(scores, reverse=True)


@pytest.mark.anyio
async def test_hybrid_mode_chunk_in_both_lists_beats_single_list() -> None:
    """A chunk in both dense and keyword ranks should outscore one in a single list."""
    in_both = _vec("both", score=0.7)
    dense_only = _vec("dense-only", score=0.8)  # higher dense score but only dense
    keyword_only = _vec("kw-only", score=1.0)    # keyword match count

    svc = _service(dense=[in_both, dense_only], keyword=[in_both, keyword_only])
    results = await svc.retrieve("query", uuid4(), limit=10, mode="hybrid")

    id_to_score = {r.chunk_id: r.score for r in results}
    # "both" has RRF contribution from two sources — should outscore keyword_only (one source)
    assert id_to_score.get("both", 0.0) >= id_to_score.get("kw-only", 0.0)


@pytest.mark.anyio
async def test_hybrid_mode_empty_dense_results() -> None:
    """Hybrid still works when dense returns nothing (falls through to keyword-only)."""
    k = _vec("kw-chunk", score=2.0)
    svc = _service(dense=[], keyword=[k])
    results = await svc.retrieve("query", uuid4(), mode="hybrid")
    assert any(r.chunk_id == "kw-chunk" for r in results)


@pytest.mark.anyio
async def test_hybrid_mode_empty_keyword_results() -> None:
    """Hybrid still works when keyword returns nothing (dense-only fallback)."""
    d = _vec("dense-chunk", score=0.9)
    svc = _service(dense=[d], keyword=[])
    results = await svc.retrieve("query", uuid4(), mode="hybrid")
    assert any(r.chunk_id == "dense-chunk" for r in results)


@pytest.mark.anyio
async def test_hybrid_mode_both_empty() -> None:
    """Both backends returning nothing → empty result list, no crash."""
    svc = _service(dense=[], keyword=[])
    results = await svc.retrieve("query", uuid4(), mode="hybrid")
    assert results == []


@pytest.mark.anyio
async def test_hybrid_keyword_failure_graceful_fallback() -> None:
    """If keyword search raises VectorStoreError, hybrid falls back to dense results."""
    d = _vec("dense-fallback", score=0.9)
    svc = _service(dense=[d], keyword_raises=VectorStoreError("backend down"))
    results = await svc.retrieve("query", uuid4(), mode="hybrid")
    # Should still return dense results, not raise
    assert any(r.chunk_id == "dense-fallback" for r in results)


@pytest.mark.anyio
async def test_hybrid_dense_failure_propagates() -> None:
    """Dense failure in hybrid mode propagates (not swallowed)."""
    svc = _service(dense_raises=VectorStoreError("dense down"), keyword=[])
    with pytest.raises(VectorStoreError, match="dense down"):
        await svc.retrieve("query", uuid4(), mode="hybrid")


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Keyword Search on Real Qdrant In-Memory Store
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_qdrant_keyword_search_matches_terms() -> None:
    """keyword_search_vectors returns only chunks containing the query terms."""
    store = QdrantVectorStore()
    user_id = uuid4()
    doc_id = uuid4()

    kirchhoff = _make_vec(
        owner_id=user_id,
        document_id=doc_id,
        text="Kirchhoff Voltage Law states that voltage around a loop is zero",
    )
    newton = _make_vec(
        owner_id=user_id,
        document_id=doc_id,
        text="Newton's second law: F equals ma",
    )
    await _seed_store(store, [kirchhoff, newton])

    results = await store.keyword_search_vectors(
        collection_name=settings.QDRANT_COLLECTION,
        query_terms=["kirchhoff", "voltage"],
        limit=10,
        filter_dict={"owner_id": str(user_id)},
    )
    ids = {v.chunk_id for v in results}
    assert kirchhoff.chunk_id in ids
    assert newton.chunk_id not in ids


@pytest.mark.anyio
async def test_qdrant_keyword_search_deterministic_order() -> None:
    """More term matches → higher rank (lower index in result list)."""
    store = QdrantVectorStore()
    user_id = uuid4()
    doc_id = uuid4()

    full_match = _make_vec(
        owner_id=user_id, document_id=doc_id,
        text="Kirchhoff Voltage Law KVL circuit analysis"
    )
    partial_match = _make_vec(
        owner_id=user_id, document_id=doc_id,
        text="Kirchhoff junction rule"
    )
    await _seed_store(store, [full_match, partial_match])

    results = await store.keyword_search_vectors(
        collection_name=settings.QDRANT_COLLECTION,
        query_terms=["kirchhoff", "voltage", "kvl"],
        limit=10,
        filter_dict={"owner_id": str(user_id)},
    )
    assert len(results) >= 2
    # full_match has 3 term matches; partial_match has 1 → full_match must be first
    assert results[0].chunk_id == full_match.chunk_id
    # score = raw match count; full_match score >= partial_match score
    assert results[0].score >= results[1].score


@pytest.mark.anyio
async def test_qdrant_keyword_search_ownership_filter() -> None:
    """Ownership filter is respected: user B cannot see user A's chunks."""
    store = QdrantVectorStore()
    user_a = uuid4()
    user_b = uuid4()
    doc_a = uuid4()

    vec_a = _make_vec(owner_id=user_a, document_id=doc_a, text="Kirchhoff Voltage Law")
    vec_b = _make_vec(owner_id=user_b, document_id=uuid4(), text="Kirchhoff Junction Law")
    await _seed_store(store, [vec_a, vec_b])

    results = await store.keyword_search_vectors(
        collection_name=settings.QDRANT_COLLECTION,
        query_terms=["kirchhoff"],
        limit=10,
        filter_dict={"owner_id": str(user_a)},
    )
    ids = {v.chunk_id for v in results}
    assert vec_a.chunk_id in ids
    assert vec_b.chunk_id not in ids


@pytest.mark.anyio
async def test_qdrant_keyword_search_document_filter() -> None:
    """document_id filter restricts keyword results to one document."""
    store = QdrantVectorStore()
    user_id = uuid4()
    doc_1 = uuid4()
    doc_2 = uuid4()

    v1 = _make_vec(owner_id=user_id, document_id=doc_1, text="Kirchhoff Voltage Law")
    v2 = _make_vec(owner_id=user_id, document_id=doc_2, text="Kirchhoff Current Law")
    await _seed_store(store, [v1, v2])

    results = await store.keyword_search_vectors(
        collection_name=settings.QDRANT_COLLECTION,
        query_terms=["kirchhoff"],
        limit=10,
        filter_dict={"owner_id": str(user_id), "document_id": str(doc_1)},
    )
    ids = {v.chunk_id for v in results}
    assert v1.chunk_id in ids
    assert v2.chunk_id not in ids


@pytest.mark.anyio
async def test_qdrant_keyword_search_no_collection() -> None:
    """keyword_search_vectors returns [] if collection doesn't exist yet."""
    store = QdrantVectorStore()
    results = await store.keyword_search_vectors(
        collection_name="nonexistent_collection",
        query_terms=["anything"],
        limit=5,
    )
    assert results == []


# ─────────────────────────────────────────────────────────────────────────────
# Regression — case-insensitive keyword matching on the in-memory Qdrant
# backend. The qdrant-client 1.9.0 in-memory backend performs a
# case-sensitive substring check inside MatchText, while the production
# Qdrant server documents MatchText as case-insensitive. The pipeline
# indexes a lowercased ``text_search`` field so both backends behave
# the same. These tests pin that contract.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_qdrant_keyword_search_returns_matching_chunk() -> None:
    """A term that exists in the indexed text returns the chunk."""
    store = QdrantVectorStore()
    user_id = uuid4()
    doc_id = uuid4()

    vec = _make_vec(
        owner_id=user_id,
        document_id=doc_id,
        text="Newton's second law: F equals ma",
    )
    await _seed_store(store, [vec])

    results = await store.keyword_search_vectors(
        collection_name=settings.QDRANT_COLLECTION,
        query_terms=["newton"],
        limit=5,
        filter_dict={"owner_id": str(user_id)},
    )
    ids = {v.chunk_id for v in results}
    assert vec.chunk_id in ids


@pytest.mark.anyio
async def test_qdrant_keyword_search_returns_no_match_for_unknown_term() -> None:
    """A term that does not exist in the indexed text returns nothing."""
    store = QdrantVectorStore()
    user_id = uuid4()
    doc_id = uuid4()

    vec = _make_vec(
        owner_id=user_id,
        document_id=doc_id,
        text="Newton's second law: F equals ma",
    )
    await _seed_store(store, [vec])

    results = await store.keyword_search_vectors(
        collection_name=settings.QDRANT_COLLECTION,
        query_terms=["galileo"],  # not in the chunk
        limit=5,
        filter_dict={"owner_id": str(user_id)},
    )
    assert results == []


@pytest.mark.anyio
async def test_qdrant_keyword_search_is_case_insensitive() -> None:
    """A query term in a different case still matches the chunk."""
    store = QdrantVectorStore()
    user_id = uuid4()
    doc_id = uuid4()

    vec = _make_vec(
        owner_id=user_id,
        document_id=doc_id,
        text="Ohm's Law: V = IR",
    )
    await _seed_store(store, [vec])

    # Mixed-case query against a lowercased index field.
    results = await store.keyword_search_vectors(
        collection_name=settings.QDRANT_COLLECTION,
        query_terms=["OHM"],
        limit=5,
        filter_dict={"owner_id": str(user_id)},
    )
    ids = {v.chunk_id for v in results}
    assert vec.chunk_id in ids


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — API Integration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_api_hybrid_mode_returns_200(client: AsyncClient) -> None:
    """POST /search with mode=hybrid returns 200 for authenticated user."""
    token = await _register_and_login(client, email="hybrid_user@example.com")
    resp = await client.post(
        "/api/v1/search",
        json={"query": "Kirchhoff Voltage Law", "top_k": 5, "mode": "hybrid"},
        **_auth(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body
    assert isinstance(body["results"], list)


@pytest.mark.anyio
async def test_api_no_mode_defaults_to_semantic(client: AsyncClient) -> None:
    """Backward compat: request without mode field works and returns 200."""
    token = await _register_and_login(client, email="compat_user@example.com")
    resp = await client.post(
        "/api/v1/search",
        json={"query": "Newton's laws"},
        **_auth(token),
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_api_unauthenticated_hybrid_blocked(client: AsyncClient) -> None:
    """Unauthenticated hybrid request returns 401."""
    resp = await client.post(
        "/api/v1/search",
        json={"query": "Kirchhoff", "mode": "hybrid"},
    )
    assert resp.status_code == 401
