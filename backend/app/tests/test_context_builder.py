"""Tests for the RAG context builder."""
from __future__ import annotations

from uuid import uuid4

from app.rag.context_builder import ContextBuilder
from app.schemas.search import RetrievedChunk


def _chunk(text: str, *, index: int = 0, page: int | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chunk-{index}",
        document_id=uuid4(),
        text=text,
        score=0.9,
        page_number=page,
        chunk_index=index,
        metadata={"page": page} if page else {},
    )


def test_build_context_empty() -> None:
    """No chunks → empty context string."""
    cb = ContextBuilder()
    assert cb.build_context([]) == ""


def test_build_context_single_chunk() -> None:
    """A single chunk renders as a [SOURCE 1] block."""
    cb = ContextBuilder()
    out = cb.build_context([_chunk("Hello world", index=0)])
    assert "[SOURCE 1]" in out
    assert "Hello world" in out
    assert out.count("[SOURCE") == 1


def test_build_context_numbers_in_order() -> None:
    """Indices are 1-based and match chunk order."""
    cb = ContextBuilder()
    chunks = [_chunk("A", index=0), _chunk("B", index=1), _chunk("C", index=2)]
    out = cb.build_context(chunks)
    assert "[SOURCE 1]" in out
    assert "[SOURCE 2]" in out
    assert "[SOURCE 3]" in out
    # Order preserved
    assert out.index("[SOURCE 1]") < out.index("[SOURCE 2]") < out.index("[SOURCE 3]")


def test_build_context_max_chunks_cap() -> None:
    """max_chunks truncates the input."""
    cb = ContextBuilder()
    chunks = [_chunk(f"text {i}", index=i) for i in range(5)]
    out = cb.build_context(chunks, max_chunks=2)
    assert "[SOURCE 1]" in out
    assert "[SOURCE 2]" in out
    assert "[SOURCE 3]" not in out


def test_build_context_preserves_text() -> None:
    """Chunk text is included verbatim."""
    cb = ContextBuilder()
    text = "Faraday's law of induction states that EMF equals -dPhi/dt"
    out = cb.build_context([_chunk(text)])
    assert text in out


def test_build_context_empty_chunk_text_falls_back() -> None:
    """Defensive: an empty chunk text is replaced with a placeholder
    so we never emit a header with no body."""
    cb = ContextBuilder()
    out = cb.build_context([_chunk("", index=0)])
    assert "[SOURCE 1]" in out
    assert "empty source excerpt" in out


def test_build_user_prompt_with_context() -> None:
    """User prompt joins context + query with clear labels."""
    cb = ContextBuilder()
    out = cb.build_user_prompt("What is Ohm's law?", "[SOURCE 1]\nV=IR")
    assert "Sources:" in out
    assert "[SOURCE 1]" in out
    assert "Question:" in out
    assert "What is Ohm's law?" in out


def test_build_user_prompt_empty_context() -> None:
    """User prompt without context tells the model no sources were found."""
    cb = ContextBuilder()
    out = cb.build_user_prompt("What is Ohm's law?", "")
    assert "No relevant sources" in out
    assert "What is Ohm's law?" in out


def test_build_user_prompt_strips_query_whitespace() -> None:
    """Query is trimmed; trailing newline doesn't survive."""
    cb = ContextBuilder()
    out = cb.build_user_prompt("   hello   ", "ctx")
    assert "Question:\nhello" in out