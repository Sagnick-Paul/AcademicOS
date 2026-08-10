"""Diagnostic: trace where document_id diverges in test_get_session_returns_messages_in_order."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.db.models.document import Document
from app.main import app
from app.processing.embeddings import BaseEmbeddingProvider, BaseVectorStore, EmbeddingVector
from app.rag.service import RAGService
from app.services.chat_service import ChatService
from app.services.retrieval_service import RetrievalService
from app.tests.test_chat import (
    _auth, _register_and_login, _FakeLLM, _vec_for_doc,
    _fake_rag_service_with_doc, _vec,
)


class _MockEmb(BaseEmbeddingProvider):
    async def generate_embeddings(self, texts):
        return [[0.0] * 384 for _ in texts]
    async def generate_embedding(self, text):
        return [0.0] * 384


class _MockVS(BaseVectorStore):
    def __init__(self, chunks):
        self.chunks = chunks
    async def create_collection(self, *a, **k): pass
    async def upsert_vectors(self, *a, **k): pass
    async def delete_vectors(self, *a, **k): pass
    async def search_vectors(self, *a, **k): return self.chunks
    async def keyword_search_vectors(self, *a, **k): return self.chunks


@pytest.mark.anyio
async def test_diag_trace_ids(client, db_session):
    """Trace ID at every step of the failing test."""
    from sqlalchemy import select

    # 1. Register user
    token = await _register_and_login(client, email="trace@example.com")

    # 2. Create session with initial_query
    r = await client.post(
        "/api/v1/chat/sessions",
        json={"initial_query": "first question"},
        **_auth(token),
    )
    session_id = r.json()["id"]
    print(f"\n=== SESSION id={session_id!r}")

    # 3. Upload a doc
    files = {"file": ("notes.pdf", b"%PDF-1.4\n%fake pdf body\n", "application/pdf")}
    up = await client.post("/api/v1/documents/upload", files=files, **_auth(token))
    assert up.status_code == 201, up.text
    up_json = up.json()
    print(f"=== UPLOAD response: {up_json}")
    print(f"=== UPLOAD response keys: {list(up_json.keys())}")

    # 4. Get doc_id from response — check what field the test extracts
    doc_id_from_response = up_json["id"]
    print(f"=== DOC id from response (using up_json['id']): {doc_id_from_response!r}")

    # 5. Look up actual document in DB by that ID
    result = await db_session.execute(
        select(Document).where(Document.id == doc_id_from_response)
    )
    doc_db = result.scalar_one_or_none()
    print(f"=== DOC in DB by response id: {doc_db}")
    if doc_db:
        print(f"  doc_db.id={doc_db.id!r}")
        print(f"  doc_db.owner_id={doc_db.owner_id!r}")

    # 6. List ALL documents in DB to see what the user actually has
    result = await db_session.execute(
        select(Document)
    )
    all_docs = result.scalars().all()
    print(f"=== ALL documents in DB: {len(all_docs)}")
    for d in all_docs:
        print(f"  {d.id!r} owner={d.owner_id!r} filename={d.original_filename!r} status={d.upload_status!r}")

    # 7. Now build the fake RAG with the doc_id from the upload response
    fake_rag = _fake_rag_service_with_doc(
        doc_id_from_response, chunks=[_vec("real chunk", page=2, chunk_index=0)],
    )
    # Inspect the chunks inside fake_rag
    ret_svc = fake_rag.retrieval_service
    vs = ret_svc.vector_store
    if hasattr(vs, "dense_results"):
        for ch in vs.dense_results:
            print(f"=== VECTOR chunk: chunk_id={ch.chunk_id} metadata={ch.metadata}")
    else:
        for ch in vs.chunks:
            print(f"=== VECTOR chunk: chunk_id={ch.chunk_id} metadata={ch.metadata}")

    # 8. Call the RAG service directly to see what chunks/sources come back
    from app.db.models.user import User
    result = await db_session.execute(
        select(User)
    )
    users = result.scalars().all()
    for u in users:
        print(f"=== USER db: {u.id!r} email={u.email}")

    # 9. Now call send_message and see what happens
    # First, we need to find the right user
    from sqlalchemy import select as _sel
    result = await db_session.execute(
        _sel(User).where(User.email == "trace@example.com")
    )
    user = result.scalar_one()
    print(f"=== USER for trace: {user.id!r}")

    # 10. Get the chat source document_id by calling RAG directly
    from app.rag.service import RAGService
    answer = await fake_rag.answer_question(
        query="second question",
        owner_id=user.id,
        document_id=doc_id_from_response,
    )
    print(f"=== RAG answer.sources:")
    for src in answer.sources:
        print(f"  src.document_id={src.document_id!r} src.chunk_id={src.chunk_id!r}")
        print(f"  === COMPARE: src.document_id == uploaded doc_id? {src.document_id == doc_id_from_response}")
