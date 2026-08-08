"""Tests for Phase 2 — Step 2: Embedding & Vector Indexing Foundation."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import pytest

from app.core.config import settings
from app.processing.exceptions import EmbeddingGenerationFailed, VectorStoreError
from app.processing.embeddings import (
    SentenceTransformerEmbeddingProvider,
    QdrantVectorStore,
    EmbeddingVector,
    get_embedding_provider,
)
from app.processing.pipeline import DocumentProcessingPipeline


@pytest.mark.anyio
async def test_embedding_generation() -> None:
    """Test embedding generation for single and multiple texts."""
    provider = SentenceTransformerEmbeddingProvider()
    
    # Test single text embedding
    embedding = await provider.generate_embedding("Hello world")
    assert isinstance(embedding, list)
    assert len(embedding) == settings.EMBEDDING_DIMENSION
    assert all(isinstance(val, float) for val in embedding)

    # Test batch text embedding
    texts = ["First chunk", "Second chunk", "Third chunk"]
    embeddings = await provider.generate_embeddings(texts)
    assert len(embeddings) == len(texts)
    for emb in embeddings:
        assert len(emb) == settings.EMBEDDING_DIMENSION

    # Test empty batch
    empty_result = await provider.generate_embeddings([])
    assert empty_result == []


@pytest.mark.anyio
async def test_qdrant_vector_store() -> None:
    """Test Qdrant collection creation, upsertion, deletion, and searching."""
    store = QdrantVectorStore()
    collection_name = "test_collection"
    
    # 1. Create collection
    await store.create_collection(collection_name=collection_name, vector_size=384)
    
    # Check that creating again does not fail
    await store.create_collection(collection_name=collection_name, vector_size=384)

    # 2. Upsert vectors
    chunk_1 = str(uuid4())
    chunk_2 = str(uuid4())
    
    vec1 = [0.1] * 384
    vec2 = [0.2] * 384
    
    vectors = [
        EmbeddingVector(chunk_id=chunk_1, vector=vec1, metadata={"document_id": "doc_1", "text": "chunk one"}),
        EmbeddingVector(chunk_id=chunk_2, vector=vec2, metadata={"document_id": "doc_1", "text": "chunk two"}),
    ]
    
    await store.upsert_vectors(collection_name=collection_name, vectors=vectors)

    # 3. Search vectors
    search_results = await store.search_vectors(
        collection_name=collection_name,
        query_vector=vec1,
        limit=5,
        filter_dict={"document_id": "doc_1"}
    )
    assert len(search_results) == 2
    assert search_results[0].chunk_id in (chunk_1, chunk_2)
    
    # Test search with filter matching nothing
    empty_search = await store.search_vectors(
        collection_name=collection_name,
        query_vector=vec1,
        limit=5,
        filter_dict={"document_id": "non_existent"}
    )
    assert len(empty_search) == 0

    # 4. Delete vectors
    await store.delete_vectors(collection_name=collection_name, filter_dict={"document_id": "doc_1"})
    
    # Search again to verify deletion
    post_delete_search = await store.search_vectors(
        collection_name=collection_name,
        query_vector=vec1,
        limit=5,
    )
    assert len(post_delete_search) == 0


@pytest.mark.anyio
async def test_duplicate_upsert_handling() -> None:
    """Test Qdrant upsert idempotency when handling duplicate keys."""
    store = QdrantVectorStore()
    collection_name = "test_duplicate_collection"
    await store.create_collection(collection_name=collection_name, vector_size=384)

    chunk_id = str(uuid4())
    vec1 = [0.5] * 384
    vec2 = [0.9] * 384

    # First upsert
    v1 = EmbeddingVector(chunk_id=chunk_id, vector=vec1, metadata={"version": 1})
    await store.upsert_vectors(collection_name, [v1])

    # Second upsert (same chunk_id, different vector and metadata)
    v2 = EmbeddingVector(chunk_id=chunk_id, vector=vec2, metadata={"version": 2})
    await store.upsert_vectors(collection_name, [v2])

    # Search should return only one point (idempotent overwrite)
    results = await store.search_vectors(collection_name, query_vector=vec2, limit=5)
    assert len(results) == 1
    assert results[0].chunk_id == chunk_id
    assert results[0].metadata["version"] == 2


def test_unsupported_provider_handling() -> None:
    """Verify correct exception behavior for unsupported/unimplemented providers."""
    # Supported
    p1 = get_embedding_provider("local")
    assert isinstance(p1, SentenceTransformerEmbeddingProvider)
    
    p2 = get_embedding_provider("sentence-transformers")
    assert isinstance(p2, SentenceTransformerEmbeddingProvider)

    # Unimplemented but known
    with pytest.raises(ValueError, match="is not implemented yet"):
        get_embedding_provider("gemini")

    # Totally unsupported
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        get_embedding_provider("unsupported_provider_name")


@pytest.mark.anyio
async def test_pipeline_integration(tmp_path: Path) -> None:
    """Verify the end-to-end embedding generation & storing in the processing pipeline."""
    # Create test text file
    txt_path = tmp_path / "integration_test.txt"
    txt_path.write_text("This is an integration test. It contains enough text to chunk and embed.", encoding="utf-8")

    provider = SentenceTransformerEmbeddingProvider()
    store = QdrantVectorStore()
    
    # Run pipeline with dependency injection
    pipeline = DocumentProcessingPipeline(
        embedding_provider=provider,
        vector_store=store,
    )
    
    doc_id = uuid4()
    result = await pipeline.run(
        file_path=txt_path,
        file_type="txt",
        filename="integration_test.txt",
        file_size=len(txt_path.read_bytes()),
        document_id=doc_id,
    )
    
    assert len(result.chunks) > 0
    
    # Verify that the vector collection contains our embedded chunks
    search_res = await store.search_vectors(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=[0.0] * settings.EMBEDDING_DIMENSION,
        limit=10,
        filter_dict={"document_id": str(doc_id)}
    )
    assert len(search_res) == len(result.chunks)
    for point in search_res:
        assert point.metadata["document_id"] == str(doc_id)
        assert "chunk_index" in point.metadata
        assert "text" in point.metadata["metadata"]
