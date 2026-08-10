"""Tests for Phase 2 — Step 5: RAG service + /chat endpoint, and Phase 3
persistent session-based chat."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.api.deps import get_rag_service
from app.core.config import settings
from app.db.models.enums import ChatRole
from app.llm.exceptions import (
    LLMError,
    LLMProviderUnavailable,
    LLMRequestRejected,
)
from app.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from app.main import app
from app.processing.embeddings import (
    BaseEmbeddingProvider,
    BaseVectorStore,
    EmbeddingVector,
)
from app.rag.context_builder import ContextBuilder
from app.rag.exceptions import NoRelevantContextError
from app.rag.grounding_prompt import GROUNDING_SYSTEM_PROMPT
from app.rag.service import ChatSource, RAGAnswer, RAGService
from app.services.chat_service import ChatService
from app.services.exceptions import DocumentNotFoundError
from app.services.retrieval_service import RetrievalService
from app.tests.conftest import _db_session_dep  # noqa: F401 — used via app.dependency_overrides


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


# ─── Mock backends (mirror test_search.py) ─────────────────────────────────────


class _MockEmbedding(BaseEmbeddingProvider):
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * settings.EMBEDDING_DIMENSION for _ in texts]

    async def generate_embedding(self, text: str) -> List[float]:
        return [0.0] * settings.EMBEDDING_DIMENSION


class _MockVectorStore(BaseVectorStore):
    def __init__(self, dense_results: Optional[List[EmbeddingVector]] = None) -> None:
        self.dense_results = dense_results or []

    async def create_collection(self, collection_name, vector_size): pass
    async def upsert_vectors(self, collection_name, vectors): pass
    async def delete_vectors(self, collection_name, filter_dict): pass

    async def search_vectors(
        self, collection_name, query_vector, limit=10,
        filter_dict=None, score_threshold=None,
    ) -> List[EmbeddingVector]:
        return self.dense_results[:limit]

    async def keyword_search_vectors(
        self, collection_name, query_terms, limit=10, filter_dict=None,
    ) -> List[EmbeddingVector]:
        return self.dense_results[:limit]


def _vec(
    text: str,
    *,
    score: float = 0.9,
    page: int | None = 1,
    chunk_index: int = 0,
) -> EmbeddingVector:
    return EmbeddingVector(
        chunk_id=str(uuid4()),
        vector=[0.0],
        score=score,
        metadata={
            "owner_id": str(uuid4()),
            "document_id": str(uuid4()),
            "page_number": page,
            "chunk_index": chunk_index,
            "metadata": {"text": text},
        },
    )


def _make_retrieved_chunk(
    text: str,
    *,
    score: float = 0.9,
    page: int | None = 1,
    chunk_index: int = 0,
):
    """Build a proper RetrievedChunk (what RAGService consumes)."""
    from app.schemas.search import RetrievedChunk

    return RetrievedChunk(
        chunk_id=str(uuid4()),
        document_id=uuid4(),
        text=text,
        score=score,
        page_number=page,
        chunk_index=chunk_index,
        metadata={},
    )


def _retrieval_service_with(chunks: List[EmbeddingVector]) -> RetrievalService:
    return RetrievalService(
        embedding_provider=_MockEmbedding(),
        vector_store=_MockVectorStore(dense_results=chunks),
    )


# ─── Mock LLM (independent of MockLLMProvider so we control failures) ────────


@dataclass
class _FakeLLM:
    """Drop-in replacement for BaseLLMProvider used by RAG service tests."""
    text: str = "Mock answer."
    fail_with: Optional[Exception] = None
    captured_requests: List[LLMRequest] = field(default_factory=list)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.captured_requests.append(request)
        if self.fail_with is not None:
            raise self.fail_with
        return LLMResponse(text=self.text, model="fake-llm")


# ─────────────────────────────────────────────────────────────────────────────
# Grounding prompt
# ─────────────────────────────────────────────────────────────────────────────


def test_grounding_prompt_has_no_instructions_injection() -> None:
    """Prompt must not leak its own internals to the model."""
    # Collapse runs of whitespace so wrapped phrases match.
    normalised = " ".join(GROUNDING_SYSTEM_PROMPT.split())
    assert "I cannot answer this based on the provided documents" in normalised
    assert "[SOURCE" in GROUNDING_SYSTEM_PROMPT
    assert "[n]" in GROUNDING_SYSTEM_PROMPT


def test_grounding_prompt_is_nonempty_string() -> None:
    assert isinstance(GROUNDING_SYSTEM_PROMPT, str)
    assert len(GROUNDING_SYSTEM_PROMPT) > 50


# ─────────────────────────────────────────────────────────────────────────────
# RAGService — orchestration
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_rag_service_calls_retrieval_then_llm() -> None:
    """End-to-end happy path: retrieval → context → LLM → answer + sources."""
    chunks = [
        _vec("Faraday's law: EMF equals -dPhi/dt", page=3, chunk_index=0),
        _vec("Lenz's law: induced current opposes the change", page=4, chunk_index=1),
    ]
    svc = RAGService(
        retrieval_service=_retrieval_service_with(chunks),
        llm_provider=_FakeLLM(text="The model says hello."),
    )
    answer = await svc.answer_question(
        query="What is Faraday's law?",
        owner_id=uuid4(),
        top_k=5,
    )

    assert answer.answer == "The model says hello."
    assert answer.model == "fake-llm"
    assert len(answer.sources) == 2
    assert answer.sources[0].index == 1
    assert answer.sources[1].index == 2
    assert answer.sources[0].page_number == 3
    assert answer.sources[1].page_number == 4
    assert answer.retrieval_mode == "semantic"


@pytest.mark.anyio
async def test_rag_service_builds_numbered_prompt() -> None:
    """Context block is fed to the LLM with [SOURCE n] headers."""
    chunks = [_vec("apple banana cherry")]
    fake_llm = _FakeLLM()
    svc = RAGService(
        retrieval_service=_retrieval_service_with(chunks),
        llm_provider=fake_llm,
    )
    await svc.answer_question(query="fruit", owner_id=uuid4())

    assert len(fake_llm.captured_requests) == 1
    req = fake_llm.captured_requests[0]
    # System message is the grounding prompt
    assert req.messages[0].role == "system"
    assert req.messages[0].content == GROUNDING_SYSTEM_PROMPT
    # User message contains the [SOURCE 1] header
    assert req.messages[1].role == "user"
    assert "[SOURCE 1]" in req.messages[1].content
    assert "apple banana cherry" in req.messages[1].content
    assert "fruit" in req.messages[1].content


@pytest.mark.anyio
async def test_rag_service_passes_mode_to_retrieval() -> None:
    """mode='hybrid' reaches the retrieval service unchanged."""
    captured_mode: Dict[str, Any] = {}

    class _CapturingRetrieval:
        async def retrieve(self, **kwargs):
            captured_mode.update(kwargs)
            return [_make_retrieved_chunk("hybrid chunk")]

    svc = RAGService(
        retrieval_service=_CapturingRetrieval(),  # type: ignore[arg-type]
        llm_provider=_FakeLLM(text="x"),
    )
    await svc.answer_question(
        query="q", owner_id=uuid4(), mode="hybrid"
    )
    assert captured_mode["mode"] == "hybrid"


@pytest.mark.anyio
async def test_rag_service_passes_document_filter() -> None:
    """document_id filter reaches the retrieval service."""
    captured: Dict[str, Any] = {}
    doc_id = uuid4()

    class _CapturingRetrieval:
        async def retrieve(self, **kwargs):
            captured.update(kwargs)
            return [_make_retrieved_chunk("filtered chunk")]

    svc = RAGService(
        retrieval_service=_CapturingRetrieval(),  # type: ignore[arg-type]
        llm_provider=_FakeLLM(text="x"),
    )
    await svc.answer_question(
        query="q", owner_id=uuid4(), document_id=doc_id,
    )
    assert captured["document_id"] == doc_id


@pytest.mark.anyio
async def test_rag_service_raises_when_no_context() -> None:
    """Empty retrieval → NoRelevantContextError, no LLM call."""
    fake_llm = _FakeLLM()
    svc = RAGService(
        retrieval_service=_retrieval_service_with([]),
        llm_provider=fake_llm,
    )
    with pytest.raises(NoRelevantContextError):
        await svc.answer_question(query="missing", owner_id=uuid4())
    # LLM must NOT have been called
    assert fake_llm.captured_requests == []


@pytest.mark.anyio
async def test_rag_service_propagates_llm_errors() -> None:
    """LLM failures surface as LLMError (no masking)."""
    svc = RAGService(
        retrieval_service=_retrieval_service_with([_vec("anything")]),
        llm_provider=_FakeLLM(fail_with=LLMProviderUnavailable("backend down")),
    )
    with pytest.raises(LLMError, match="backend down"):
        await svc.answer_question(query="q", owner_id=uuid4())


@pytest.mark.anyio
async def test_rag_service_propagates_request_rejected() -> None:
    """LLMRequestRejected (auth/quota) also surfaces unchanged."""
    svc = RAGService(
        retrieval_service=_retrieval_service_with([_vec("anything")]),
        llm_provider=_FakeLLM(fail_with=LLMRequestRejected("429")),
    )
    with pytest.raises(LLMRequestRejected):
        await svc.answer_question(query="q", owner_id=uuid4())


@pytest.mark.anyio
async def test_rag_service_surfaces_scores_and_metadata() -> None:
    """ChatSource exposes score, chunk_index, page_number from chunks."""
    chunks = [
        _vec("a", score=0.92, page=5, chunk_index=2),
        _vec("b", score=0.71, page=5, chunk_index=3),
    ]
    svc = RAGService(
        retrieval_service=_retrieval_service_with(chunks),
        llm_provider=_FakeLLM(),
    )
    answer = await svc.answer_question(query="q", owner_id=uuid4())
    src0 = answer.sources[0]
    assert src0.score == 0.92
    assert src0.chunk_index == 2
    assert src0.page_number == 5
    assert src0.snippet == "a"


@pytest.mark.anyio
async def test_rag_service_snippet_truncation() -> None:
    """Long chunk texts are truncated to <= 280 chars in the snippet."""
    long_text = "word " * 200  # ~1000 chars
    chunks = [_vec(long_text)]
    svc = RAGService(
        retrieval_service=_retrieval_service_with(chunks),
        llm_provider=_FakeLLM(),
    )
    answer = await svc.answer_question(query="q", owner_id=uuid4())
    assert len(answer.sources[0].snippet) <= 280
    assert answer.sources[0].snippet.endswith("...")


@pytest.mark.anyio
async def test_rag_service_uses_default_context_builder() -> None:
    """RAGService constructs its own ContextBuilder by default."""
    svc = RAGService(
        retrieval_service=_retrieval_service_with([_vec("text")]),
        llm_provider=_FakeLLM(),
    )
    assert isinstance(svc.context_builder, ContextBuilder)


# ─────────────────────────────────────────────────────────────────────────────
# /api/v1/chat endpoint
# ─────────────────────────────────────────────────────────────────────────────


def _fake_rag_service(
    chunks: List[EmbeddingVector] | None = None,
    *,
    fail_with: Exception | None = None,
    empty: bool = False,
) -> RAGService:
    """Build a real RAGService with fake backends (no network, no DB)."""
    if chunks is None and not empty:
        chunks = [_vec("chunk text", page=1, chunk_index=0)]
    if empty:
        chunks = []
    fake_llm = _FakeLLM(text="This is the answer.", fail_with=fail_with)
    return RAGService(
        retrieval_service=_retrieval_service_with(chunks or []),
        llm_provider=fake_llm,
    )


def _vec_for_doc(
    text: str,
    doc_id: UUID,
    *,
    score: float = 0.9,
    page: int | None = 1,
    chunk_index: int = 0,
) -> EmbeddingVector:
    """Build a chunk whose metadata refers to a real document the user owns."""
    return EmbeddingVector(
        chunk_id=str(uuid4()),
        vector=[0.0],
        score=score,
        metadata={
            "owner_id": str(uuid4()),
            "document_id": str(doc_id),
            "page_number": page,
            "chunk_index": chunk_index,
            "metadata": {"text": text},
        },
    )


def _fake_rag_service_with_doc(
    doc_id: UUID,
    *,
    chunks: List[EmbeddingVector] | None = None,
    fail_with: Exception | None = None,
    text: str = "This is the answer.",
) -> RAGService:
    """Build a fake RAG service whose chunks reference a real document."""
    if chunks is None:
        chunks = [_vec_for_doc("chunk text", doc_id)]
    fake_llm = _FakeLLM(text=text, fail_with=fail_with)
    return RAGService(
        retrieval_service=_retrieval_service_with(chunks),
        llm_provider=fake_llm,
    )


@pytest.mark.anyio
async def test_api_chat_unauthenticated_returns_401(client: AsyncClient) -> None:
    """No token → 401."""
    r = await client.post("/api/v1/chat", json={"query": "What is X?"})
    assert r.status_code == 401


@pytest.mark.anyio
async def test_api_chat_empty_query_rejected(client: AsyncClient) -> None:
    """Empty query is rejected by Pydantic validation → 422."""
    token = await _register_and_login(client, email="chat_empty@example.com")
    r = await client.post(
        "/api/v1/chat", json={"query": "   "}, **_auth(token),
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_api_chat_invalid_mode_rejected(client: AsyncClient) -> None:
    """Invalid mode string is rejected by Pydantic literal validator → 422."""
    token = await _register_and_login(client, email="chat_mode@example.com")
    r = await client.post(
        "/api/v1/chat", json={"query": "q", "mode": "fuzzy"}, **_auth(token),
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_api_chat_no_relevant_context_returns_clean_response(
    client: AsyncClient,
) -> None:
    """Empty retrieval → 200 with polite refusal, no LLM call, empty sources."""
    token = await _register_and_login(client, email="chat_nocontext@example.com")

    app.dependency_overrides[get_rag_service] = lambda: _fake_rag_service(empty=True)
    try:
        r = await client.post(
            "/api/v1/chat",
            json={"query": "anything"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert r.status_code == 200
    body = r.json()
    assert body["sources"] == []
    assert "cannot answer" in body["answer"].lower()


@pytest.mark.anyio
async def test_api_chat_success_returns_answer_and_sources(
    client: AsyncClient,
) -> None:
    """Happy path: 200 with answer text + at least one source."""
    token = await _register_and_login(client, email="chat_ok@example.com")

    app.dependency_overrides[get_rag_service] = lambda: _fake_rag_service()
    try:
        r = await client.post(
            "/api/v1/chat",
            json={"query": "What is the law?", "top_k": 3},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "This is the answer."
    assert isinstance(body["sources"], list)
    assert len(body["sources"]) >= 1
    src = body["sources"][0]
    assert src["index"] == 1
    assert "chunk_id" in src
    assert "snippet" in src


@pytest.mark.anyio
async def test_api_chat_passes_hybrid_mode_to_service(client: AsyncClient) -> None:
    """mode='hybrid' is forwarded to RAGService."""
    token = await _register_and_login(client, email="chat_hybrid@example.com")

    # Spy that captures the call
    captured: Dict[str, Any] = {}

    class _SpyService(RAGService):
        async def answer_question(self, **kwargs):
            captured.update(kwargs)
            return await super().answer_question(**kwargs)

    svc = _SpyService(
        retrieval_service=_retrieval_service_with([_vec("hi")]),
        llm_provider=_FakeLLM(text="ok"),
    )

    app.dependency_overrides[get_rag_service] = lambda: svc
    try:
        r = await client.post(
            "/api/v1/chat",
            json={"query": "q", "mode": "hybrid"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert r.status_code == 200
    assert captured["mode"] == "hybrid"


@pytest.mark.anyio
async def test_api_chat_llm_failure_returns_503(client: AsyncClient) -> None:
    """LLMError → 503 (no stack trace leaked)."""
    token = await _register_and_login(client, email="chat_fail@example.com")

    svc = _fake_rag_service(
        fail_with=LLMProviderUnavailable("provider is down"),
    )
    app.dependency_overrides[get_rag_service] = lambda: svc
    try:
        r = await client.post(
            "/api/v1/chat",
            json={"query": "q"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert r.status_code == 503
    body = r.json()
    # Must NOT leak the provider name / exception details
    assert "provider is down" not in body["detail"]
    assert "provider is down" not in str(body)


@pytest.mark.anyio
async def test_api_chat_unauthorized_document_returns_404(
    client: AsyncClient,
) -> None:
    """A document_id belonging to another user → 404 (not 403)."""
    # Register user A
    token_a = await _register_and_login(client, email="chat_doc_a@example.com")
    # Register user B, create a document
    token_b = await _register_and_login(client, email="chat_doc_b@example.com")

    # User B uploads a small PDF
    files = {"file": ("notes.pdf", b"%PDF-1.4\n%fake pdf body\n", "application/pdf")}
    up = await client.post(
        "/api/v1/documents/upload", files=files, **_auth(token_b),
    )
    assert up.status_code == 201, up.text
    other_doc_id = up.json()["id"]

    # User A tries to chat against user B's document
    app.dependency_overrides[get_rag_service] = lambda: _fake_rag_service()
    try:
        r = await client.post(
            "/api/v1/chat",
            json={"query": "q", "document_id": other_doc_id},
            **_auth(token_a),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert r.status_code == 404


@pytest.mark.anyio
async def test_api_chat_owned_document_succeeds(
    client: AsyncClient,
) -> None:
    """A user may pass their own document_id and get a successful answer."""
    token = await _register_and_login(client, email="chat_own_doc@example.com")

    files = {"file": ("notes.pdf", b"%PDF-1.4\n%fake pdf body\n", "application/pdf")}
    up = await client.post(
        "/api/v1/documents/upload", files=files, **_auth(token),
    )
    assert up.status_code == 201, up.text
    own_doc_id = up.json()["id"]

    app.dependency_overrides[get_rag_service] = lambda: _fake_rag_service()
    try:
        r = await client.post(
            "/api/v1/chat",
            json={"query": "q", "document_id": own_doc_id},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert r.status_code == 200


@pytest.mark.anyio
async def test_api_chat_top_k_validation(client: AsyncClient) -> None:
    """top_k out of range is rejected by Pydantic → 422."""
    token = await _register_and_login(client, email="chat_topk@example.com")
    r = await client.post(
        "/api/v1/chat", json={"query": "q", "top_k": 0}, **_auth(token),
    )
    assert r.status_code == 422
    r = await client.post(
        "/api/v1/chat", json={"query": "q", "top_k": 999}, **_auth(token),
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_api_chat_response_shape(client: AsyncClient) -> None:
    """Response includes model, retrieval_mode, and token fields."""
    token = await _register_and_login(client, email="chat_shape@example.com")

    app.dependency_overrides[get_rag_service] = lambda: _fake_rag_service()
    try:
        r = await client.post(
            "/api/v1/chat",
            json={"query": "q", "mode": "semantic"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert r.status_code == 200
    body = r.json()
    for field in ("answer", "sources", "model", "retrieval_mode"):
        assert field in body
    assert body["retrieval_mode"] in ("semantic", "hybrid")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Persistent session-based chat
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_sessions_unauthenticated_returns_401(client: AsyncClient) -> None:
    """No token → 401 for session list."""
    r = await client.get("/api/v1/chat/sessions")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_create_session_returns_201_and_links_user(
    client: AsyncClient,
) -> None:
    """Authenticated user creates a session; user_id is bound to caller."""
    token = await _register_and_login(client, email="sess_create@example.com")
    r = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "My notes"},
        **_auth(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "My notes"
    assert "id" in body
    assert "user_id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.anyio
async def test_create_session_with_initial_query_derives_title(
    client: AsyncClient,
) -> None:
    """initial_query is persisted and the title is derived deterministically."""
    token = await _register_and_login(client, email="sess_derive@example.com")
    r = await client.post(
        "/api/v1/chat/sessions",
        json={"initial_query": "Explain transformer voltage regulation"},
        **_auth(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    # Title-cased derivation, no LLM call.
    assert "Transformer" in body["title"]
    assert "Voltage" in body["title"]
    assert "Regulation" in body["title"]


@pytest.mark.anyio
async def test_create_session_with_empty_initial_query_rejected(
    client: AsyncClient,
) -> None:
    """Whitespace-only initial_query is rejected at the API level."""
    token = await _register_and_login(client, email="sess_empty@example.com")
    r = await client.post(
        "/api/v1/chat/sessions",
        json={"initial_query": "   "},
        **_auth(token),
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_create_session_with_initial_query_persists_user_message(
    client: AsyncClient,
) -> None:
    """When initial_query is given, the user message is persisted."""
    token = await _register_and_login(client, email="sess_seed@example.com")
    r = await client.post(
        "/api/v1/chat/sessions",
        json={"initial_query": "Explain transformer voltage regulation."},
        **_auth(token),
    )
    assert r.status_code == 201, r.text
    session_id = r.json()["id"]

    # Fetch the session with messages.
    g = await client.get(
        f"/api/v1/chat/sessions/{session_id}", **_auth(token),
    )
    assert g.status_code == 200, g.text
    msgs = g.json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert "transformer voltage regulation" in msgs[0]["content"]


@pytest.mark.anyio
async def test_list_sessions_returns_only_caller_sessions(
    client: AsyncClient,
) -> None:
    """User A's sessions are not visible to user B."""
    token_a = await _register_and_login(client, email="sess_a@example.com")
    token_b = await _register_and_login(client, email="sess_b@example.com")

    # A creates two sessions
    r1 = await client.post(
        "/api/v1/chat/sessions", json={"title": "A-1"}, **_auth(token_a),
    )
    r2 = await client.post(
        "/api/v1/chat/sessions", json={"title": "A-2"}, **_auth(token_a),
    )
    assert r1.status_code == 201 and r2.status_code == 201

    # B creates one session
    r3 = await client.post(
        "/api/v1/chat/sessions", json={"title": "B-1"}, **_auth(token_b),
    )
    assert r3.status_code == 201

    # A sees only A's
    la = await client.get("/api/v1/chat/sessions", **_auth(token_a))
    assert la.status_code == 200
    a_titles = {s["title"] for s in la.json()}
    assert a_titles == {"A-1", "A-2"}

    # B sees only B's
    lb = await client.get("/api/v1/chat/sessions", **_auth(token_b))
    assert lb.status_code == 200
    b_titles = {s["title"] for s in lb.json()}
    assert b_titles == {"B-1"}


@pytest.mark.anyio
async def test_get_session_returns_messages_in_order(
    client: AsyncClient,
) -> None:
    """GET /sessions/{id} returns messages in created_at ascending order."""
    token = await _register_and_login(client, email="sess_order@example.com")
    r = await client.post(
        "/api/v1/chat/sessions",
        json={"initial_query": "first question"},
        **_auth(token),
    )
    session_id = r.json()["id"]

    # Create a real document so the chat service's ownership check
    # on each source row passes and citations are persisted.
    files = {
        "file": ("notes.pdf", b"%PDF-1.4\n%fake pdf body\n", "application/pdf"),
    }
    up = await client.post(
        "/api/v1/documents/upload", files=files, **_auth(token),
    )
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]

    # Send a follow-up message via the public endpoint. The fake RAG
    # returns chunks referencing the real document so the chat service
    # persists sources.
    fake_rag = _fake_rag_service_with_doc(
        doc_id, chunks=[_vec_for_doc("real chunk", doc_id, page=2, chunk_index=0)],
    )
    app.dependency_overrides[get_rag_service] = lambda: fake_rag
    try:
        m = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "second question"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)
    assert m.status_code == 200, m.text

    g = await client.get(
        f"/api/v1/chat/sessions/{session_id}", **_auth(token),
    )
    assert g.status_code == 200, g.text
    msgs = g.json()["messages"]
    # initial_query seeds a USER message only; the follow-up adds
    # (USER, ASSISTANT). So we expect 3 messages, ordered chronologically.
    assert [m["role"] for m in msgs] == ["user", "user", "assistant"]
    assert msgs[0]["content"] == "first question"
    assert msgs[1]["content"] == "second question"
    assert msgs[2]["content"] == "This is the answer."
    # Sources attached to the assistant message.
    assert len(msgs[2]["sources"]) >= 1
    assert msgs[2]["sources"][0]["position"] >= 1
    assert msgs[2]["sources"][0]["document_id"] == doc_id


@pytest.mark.anyio
async def test_get_session_unauthenticated_returns_401(client: AsyncClient) -> None:
    r = await client.get(
        f"/api/v1/chat/sessions/{uuid4()}",
    )
    assert r.status_code == 401


@pytest.mark.anyio
async def test_get_session_invalid_uuid_returns_422(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="sess_invalid_uuid@example.com")
    r = await client.get(
        "/api/v1/chat/sessions/not-a-uuid", **_auth(token),
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_get_session_not_found_returns_404(client: AsyncClient) -> None:
    """A non-existent session id returns 404 (no existence leak)."""
    token = await _register_and_login(client, email="sess_nf@example.com")
    r = await client.get(
        f"/api/v1/chat/sessions/{uuid4()}", **_auth(token),
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_get_session_cross_user_returns_404(client: AsyncClient) -> None:
    """User B trying to view user A's session must get 404 (not 403)."""
    token_a = await _register_and_login(client, email="sess_cross_a@example.com")
    token_b = await _register_and_login(client, email="sess_cross_b@example.com")

    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "private"}, **_auth(token_a),
    )
    session_id = r.json()["id"]

    # B tries to read A's session
    g = await client.get(
        f"/api/v1/chat/sessions/{session_id}", **_auth(token_b),
    )
    assert g.status_code == 404


@pytest.mark.anyio
async def test_patch_session_renames(client: AsyncClient) -> None:
    """PATCH /sessions/{id} updates the title."""
    token = await _register_and_login(client, email="sess_rename@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "old"}, **_auth(token),
    )
    session_id = r.json()["id"]

    p = await client.patch(
        f"/api/v1/chat/sessions/{session_id}",
        json={"title": "new"},
        **_auth(token),
    )
    assert p.status_code == 200, p.text
    assert p.json()["title"] == "new"


@pytest.mark.anyio
async def test_patch_session_cross_user_returns_404(client: AsyncClient) -> None:
    """B cannot rename A's session."""
    token_a = await _register_and_login(client, email="sess_pa@example.com")
    token_b = await _register_and_login(client, email="sess_pb@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token_a),
    )
    session_id = r.json()["id"]

    p = await client.patch(
        f"/api/v1/chat/sessions/{session_id}",
        json={"title": "y"},
        **_auth(token_b),
    )
    assert p.status_code == 404


@pytest.mark.anyio
async def test_delete_session_removes_session_and_messages(
    client: AsyncClient,
) -> None:
    """After DELETE, the session is gone and so are its messages."""
    token = await _register_and_login(client, email="sess_del@example.com")
    r = await client.post(
        "/api/v1/chat/sessions",
        json={"initial_query": "hello"},
        **_auth(token),
    )
    session_id = r.json()["id"]

    d = await client.delete(
        f"/api/v1/chat/sessions/{session_id}", **_auth(token),
    )
    assert d.status_code == 204

    g = await client.get(
        f"/api/v1/chat/sessions/{session_id}", **_auth(token),
    )
    assert g.status_code == 404


@pytest.mark.anyio
async def test_delete_session_cross_user_returns_404(client: AsyncClient) -> None:
    """B cannot delete A's session."""
    token_a = await _register_and_login(client, email="sess_da@example.com")
    token_b = await _register_and_login(client, email="sess_db@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token_a),
    )
    session_id = r.json()["id"]

    d = await client.delete(
        f"/api/v1/chat/sessions/{session_id}", **_auth(token_b),
    )
    assert d.status_code == 404


@pytest.mark.anyio
async def test_send_message_unauthenticated_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        f"/api/v1/chat/sessions/{uuid4()}/messages",
        json={"query": "hi"},
    )
    assert r.status_code == 401


@pytest.mark.anyio
async def test_send_message_cross_user_session_returns_404(
    client: AsyncClient,
) -> None:
    """Sending a message into A's session under B's token is 404."""
    token_a = await _register_and_login(client, email="sess_ma@example.com")
    token_b = await _register_and_login(client, email="sess_mb@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token_a),
    )
    session_id = r.json()["id"]

    m = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"query": "hi"},
        **_auth(token_b),
    )
    assert m.status_code == 404


@pytest.mark.anyio
async def test_send_message_empty_query_returns_422(client: AsyncClient) -> None:
    """Empty query is rejected by Pydantic field validation."""
    token = await _register_and_login(client, email="sess_eqq@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token),
    )
    session_id = r.json()["id"]

    m = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"query": "   "},
        **_auth(token),
    )
    assert m.status_code == 422


@pytest.mark.anyio
async def test_send_message_persists_user_and_assistant_and_sources(
    client: AsyncClient,
) -> None:
    """A single message exchange is persisted end-to-end."""
    token = await _register_and_login(client, email="sess_pers@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token),
    )
    session_id = r.json()["id"]

    app.dependency_overrides[get_rag_service] = lambda: _fake_rag_service()
    try:
        m = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "what is X?"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert m.status_code == 200, m.text
    body = m.json()
    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "what is X?"
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["content"] == "This is the answer."
    assert len(body["assistant_message"]["sources"]) >= 1
    src = body["assistant_message"]["sources"][0]
    assert src["position"] >= 1
    assert "chunk_id" in src
    assert "document_id" in src
    assert "score" in src


@pytest.mark.anyio
async def test_send_message_unauthorized_document_returns_404(
    client: AsyncClient,
) -> None:
    """Passing another user's document_id returns 404."""
    token_a = await _register_and_login(client, email="sess_da2@example.com")
    token_b = await _register_and_login(client, email="sess_db2@example.com")

    # B uploads a doc
    files = {
        "file": ("notes.pdf", b"%PDF-1.4\n%fake pdf body\n", "application/pdf"),
    }
    up = await client.post(
        "/api/v1/documents/upload", files=files, **_auth(token_b),
    )
    assert up.status_code == 201, up.text
    other_doc_id = up.json()["id"]

    # A creates a session and tries to filter on B's doc
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token_a),
    )
    session_id = r.json()["id"]

    app.dependency_overrides[get_rag_service] = lambda: _fake_rag_service()
    try:
        m = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "hi", "document_id": other_doc_id},
            **_auth(token_a),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert m.status_code == 404


@pytest.mark.anyio
async def test_send_message_history_passed_to_rag(client: AsyncClient) -> None:
    """The second message includes the first exchange in the LLM prompt."""
    token = await _register_and_login(client, email="sess_hist@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token),
    )
    session_id = r.json()["id"]

    # Spy that captures the conversation_history forwarded to RAG.
    captured: Dict[str, Any] = {}

    class _SpyRAG(RAGService):
        async def answer_question(self, **kwargs):
            captured["history"] = kwargs.get("conversation_history")
            return await super().answer_question(**kwargs)

    svc = _SpyRAG(
        retrieval_service=_retrieval_service_with([_vec("alpha")]),
        llm_provider=_FakeLLM(text="ok"),
    )
    app.dependency_overrides[get_rag_service] = lambda: svc
    try:
        # First message
        await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "first question"},
            **_auth(token),
        )
        # Second message — history should be the first (user, assistant) pair
        await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "second question"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    history = captured.get("history")
    assert history is not None
    # At least 2 turns (user, assistant) from the first exchange.
    assert len(history) >= 2
    roles = [t.role for t in history]
    assert "user" in roles
    assert "assistant" in roles
    # The first user message content is in the history.
    assert any("first question" in t.content for t in history)


@pytest.mark.anyio
async def test_send_message_no_relevant_context_persists_refusal(
    client: AsyncClient,
) -> None:
    """No context → polite refusal persisted as the assistant message."""
    token = await _register_and_login(client, email="sess_nc@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token),
    )
    session_id = r.json()["id"]

    app.dependency_overrides[get_rag_service] = lambda: _fake_rag_service(empty=True)
    try:
        m = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "what?"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert m.status_code == 200, m.text
    body = m.json()
    assert "cannot answer" in body["assistant_message"]["content"].lower()
    assert body["assistant_message"]["sources"] == []
    # History still works on the next turn.
    g = await client.get(
        f"/api/v1/chat/sessions/{session_id}", **_auth(token),
    )
    msgs = g.json()["messages"]
    assert msgs[1]["role"] == "assistant"
    assert "cannot answer" in msgs[1]["content"].lower()


@pytest.mark.anyio
async def test_send_message_llm_failure_returns_503_and_rolls_back(
    client: AsyncClient,
) -> None:
    """An LLM failure surfaces as 503 and leaves no assistant message."""
    token = await _register_and_login(client, email="sess_fail@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token),
    )
    session_id = r.json()["id"]

    fake_svc = _fake_rag_service(
        fail_with=LLMProviderUnavailable("provider is down"),
    )
    app.dependency_overrides[get_rag_service] = lambda: fake_svc
    try:
        m = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "hi"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert m.status_code == 503
    # The user message is rolled back; the conversation is empty.
    g = await client.get(
        f"/api/v1/chat/sessions/{session_id}", **_auth(token),
    )
    assert g.status_code == 200
    assert g.json()["messages"] == []


@pytest.mark.anyio
async def test_send_message_retrieval_failure_returns_503(
    client: AsyncClient,
) -> None:
    """If the LLM raises a generic provider error, the endpoint maps it to 503."""
    token = await _register_and_login(client, email="sess_llmfail@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token),
    )
    session_id = r.json()["id"]

    fake_svc = _fake_rag_service(
        fail_with=LLMProviderUnavailable("backend down"),
    )
    app.dependency_overrides[get_rag_service] = lambda: fake_svc
    try:
        m = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "hi"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert m.status_code == 503


@pytest.mark.anyio
async def test_send_message_history_is_capped(client: AsyncClient) -> None:
    """Old history is dropped once CHAT_HISTORY_MESSAGE_LIMIT is exceeded."""
    token = await _register_and_login(client, email="sess_cap@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token),
    )
    session_id = r.json()["id"]

    captured: Dict[str, Any] = {}

    class _SpyRAG(RAGService):
        async def answer_question(self, **kwargs):
            captured["history"] = kwargs.get("conversation_history")
            return await super().answer_question(**kwargs)

    svc = _SpyRAG(
        retrieval_service=_retrieval_service_with([_vec("alpha")]),
        llm_provider=_FakeLLM(text="ok"),
    )
    app.dependency_overrides[get_rag_service] = lambda: svc
    try:
        # Send CHAT_HISTORY_MESSAGE_LIMIT + 6 messages; only the latest
        # CHAT_HISTORY_MESSAGE_LIMIT turns should be forwarded.
        for i in range(settings.CHAT_HISTORY_MESSAGE_LIMIT + 6):
            r = await client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"query": f"q-{i}"},
                **_auth(token),
            )
            assert r.status_code == 200, r.text
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    history = captured.get("history") or []
    # Latest turn is the latest question + assistant turn.
    assert len(history) <= settings.CHAT_HISTORY_MESSAGE_LIMIT


@pytest.mark.anyio
async def test_send_message_followup_uses_new_retrieval(
    client: AsyncClient,
) -> None:
    """Both messages trigger independent retrieval calls."""
    token = await _register_and_login(client, email="sess_retr@example.com")
    r = await client.post(
        "/api/v1/chat/sessions", json={"title": "x"}, **_auth(token),
    )
    session_id = r.json()["id"]

    calls: List[str] = []

    class _SpyRAG(RAGService):
        async def answer_question(self, **kwargs):
            calls.append(kwargs.get("query", ""))
            return await super().answer_question(**kwargs)

    svc = _SpyRAG(
        retrieval_service=_retrieval_service_with([_vec("alpha")]),
        llm_provider=_FakeLLM(text="ok"),
    )
    app.dependency_overrides[get_rag_service] = lambda: svc
    try:
        await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "first"},
            **_auth(token),
        )
        await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"query": "second"},
            **_auth(token),
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert calls == ["first", "second"]


# ─────────────────────────────────────────────────────────────────────────────
# Title derivation
# ─────────────────────────────────────────────────────────────────────────────


def test_derive_title_capitalizes_and_truncates() -> None:
    """Title derivation is deterministic and ignores punctuation."""
    title = ChatService._derive_title(
        "Why does the load's power factor affect voltage regulation?",
    )
    assert "Power" in title
    assert "Factor" in title
    assert "?" not in title
    assert len(title) <= 255


def test_derive_title_empty_string_falls_back() -> None:
    """A punctuation-only query falls back to 'New chat'."""
    assert ChatService._derive_title("???") == "New chat"


# ─────────────────────────────────────────────────────────────────────────────
# History builder
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_load_history_respects_limit(db_session, sessionmaker_) -> None:
    """The history builder caps message count and respects total chars."""
    # Build a session + many messages.
    from app.db.models.user import User
    from app.db.models.chat import ChatSession, ChatMessage
    from app.db.models.enums import ChatRole
    from app.rag.service import RAGService
    from app.services.retrieval_service import RetrievalService

    # Make a user
    user = User(
        email=f"hist_{uuid4()}@example.com",
        hashed_password="x",
        full_name="X",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    sess = ChatSession(user_id=user.id, title="t")
    db_session.add(sess)
    await db_session.flush()
    for i in range(15):
        db_session.add(ChatMessage(
            session_id=sess.id,
            role=ChatRole.USER if i % 2 == 0 else ChatRole.ASSISTANT,
            content=f"msg-{i}",
        ))
    await db_session.commit()

    # Build a minimal RAGService via the chat service
    svc = ChatService(
        session=db_session,
        rag_service=RAGService(
            retrieval_service=_retrieval_service_with([]),
            llm_provider=_FakeLLM(),
        ),
    )
    turns = await svc._load_history(sess.id)
    assert len(turns) <= settings.CHAT_HISTORY_MESSAGE_LIMIT
    # Last turn is the most recent (by chronological order of _render).
    assert turns[-1].content == "msg-14"


@pytest.mark.anyio
async def test_load_history_truncates_per_message(
    db_session, sessionmaker_,
) -> None:
    """Long messages are truncated to per-message char cap."""
    from app.db.models.user import User
    from app.db.models.chat import ChatSession, ChatMessage
    from app.db.models.enums import ChatRole
    from app.rag.service import RAGService

    user = User(
        email=f"trunc_{uuid4()}@example.com",
        hashed_password="x",
        full_name="X",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    sess = ChatSession(user_id=user.id, title="t")
    db_session.add(sess)
    await db_session.flush()
    long = "x" * (settings.CHAT_HISTORY_MESSAGE_CHAR_LIMIT + 100)
    db_session.add(ChatMessage(session_id=sess.id, role=ChatRole.USER, content=long))
    await db_session.commit()

    svc = ChatService(
        session=db_session,
        rag_service=RAGService(
            retrieval_service=_retrieval_service_with([]),
            llm_provider=_FakeLLM(),
        ),
    )
    turns = await svc._load_history(sess.id)
    assert len(turns) == 1
    assert len(turns[0].content) <= settings.CHAT_HISTORY_MESSAGE_CHAR_LIMIT
    assert turns[0].content.endswith("...")


@pytest.mark.anyio
async def test_load_history_is_deterministic_when_timestamps_tie(
    db_session, sessionmaker_,
) -> None:
    """History ordering must NOT depend solely on ``created_at`` precision.

    Regression: when many messages are inserted in a tight loop the
    SQLite ``func.now()`` server default can stamp them with the same
    second. The repository's ``ORDER BY created_at`` was then free to
    return the latest N rows in any order, so the *which-N* slice and
    the *last-element-of-the-slice* both became non-deterministic.

    The contract under test: insertion order is preserved, so the
    most recent message in the returned slice is always the one
    inserted last, regardless of timestamp precision.
    """
    from app.db.models.user import User
    from app.db.models.chat import ChatSession, ChatMessage
    from app.db.models.enums import ChatRole
    from app.rag.service import RAGService

    user = User(
        email=f"det_{uuid4()}@example.com",
        hashed_password="x",
        full_name="X",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    sess = ChatSession(user_id=user.id, title="t")
    db_session.add(sess)
    await db_session.flush()

    # Build a tight-loop batch where SQLite would otherwise collapse
    # all ``created_at`` values to the same second.
    n = 15
    for i in range(n):
        db_session.add(ChatMessage(
            session_id=sess.id,
            role=ChatRole.USER if i % 2 == 0 else ChatRole.ASSISTANT,
            content=f"m-{i}",
        ))
    await db_session.commit()

    # Sanity: the rows really do share a timestamp second in SQLite —
    # this is the precondition the production code must tolerate.
    from sqlalchemy import select
    rows = (await db_session.execute(
        select(ChatMessage.created_at)
        .where(ChatMessage.session_id == sess.id)
    )).scalars().all()
    distinct_seconds = {ts.replace(microsecond=0, tzinfo=None) for ts in rows}
    assert len(distinct_seconds) < n, (
        "Precondition not met: timestamps already distinguishable; "
        "test no longer exercises the tie."
    )

    svc = ChatService(
        session=db_session,
        rag_service=RAGService(
            retrieval_service=_retrieval_service_with([]),
            llm_provider=_FakeLLM(),
        ),
    )

    # Run the query many times. The slice and the last element must be
    # identical on every invocation.
    first_run = None
    for _ in range(20):
        turns = await svc._load_history(sess.id)
        contents = tuple(t.content for t in turns)
        if first_run is None:
            first_run = contents
        else:
            assert contents == first_run, (
                f"Non-deterministic history: {contents} != {first_run}"
            )

    assert first_run[-1] == f"m-{n - 1}", (
        f"Last turn must be the most recently inserted message; "
        f"got {first_run[-1]!r}, expected m-{n - 1!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cross-user document authorization at the service layer
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_authorize_document_rejects_foreign_doc(db_session) -> None:
    """A document belonging to another user raises DocumentNotFoundError."""
    from app.db.models.user import User
    from app.db.models.document import Document
    from app.db.models.enums import DocumentUploadStatus
    from app.rag.service import RAGService

    owner_a = User(
        email=f"own_a_{uuid4()}@example.com",
        hashed_password="x",
        full_name="A",
        is_active=True,
    )
    owner_b = User(
        email=f"own_b_{uuid4()}@example.com",
        hashed_password="x",
        full_name="B",
        is_active=True,
    )
    db_session.add_all([owner_a, owner_b])
    await db_session.flush()
    doc = Document(
        owner_id=owner_a.id,
        filename="x.pdf",
        original_filename="x.pdf",
        file_type="application/pdf",
        file_size=1,
        storage_path="x",
        upload_status=DocumentUploadStatus.READY,
    )
    db_session.add(doc)
    await db_session.flush()

    svc = ChatService(
        session=db_session,
        rag_service=RAGService(
            retrieval_service=_retrieval_service_with([]),
            llm_provider=_FakeLLM(),
        ),
    )
    with pytest.raises(DocumentNotFoundError):
        await svc._authorize_document(doc.id, owner_id=owner_b.id)


@pytest.mark.anyio
async def test_user_owns_document_returns_true_for_owner(db_session) -> None:
    """True for the owner, False for everyone else."""
    from app.db.models.user import User
    from app.db.models.document import Document
    from app.db.models.enums import DocumentUploadStatus
    from app.rag.service import RAGService

    owner = User(
        email=f"owns_{uuid4()}@example.com",
        hashed_password="x",
        full_name="X",
        is_active=True,
    )
    other = User(
        email=f"other_{uuid4()}@example.com",
        hashed_password="x",
        full_name="O",
        is_active=True,
    )
    db_session.add_all([owner, other])
    await db_session.flush()
    doc = Document(
        owner_id=owner.id,
        filename="x.pdf",
        original_filename="x.pdf",
        file_type="application/pdf",
        file_size=1,
        storage_path="x",
        upload_status=DocumentUploadStatus.READY,
    )
    db_session.add(doc)
    await db_session.flush()

    svc = ChatService(
        session=db_session,
        rag_service=RAGService(
            retrieval_service=_retrieval_service_with([]),
            llm_provider=_FakeLLM(),
        ),
    )
    assert await svc._user_owns_document(doc.id, owner_id=owner.id)
    assert not await svc._user_owns_document(doc.id, owner_id=other.id)