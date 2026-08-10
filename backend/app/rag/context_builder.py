"""Build the LLM prompt from retrieved chunks and conversation history.

The :class:`ContextBuilder` is the only place that decides:

* how a single retrieved chunk is rendered into text,
* how multiple chunks are assembled into a single context block,
* how the conversation history block is rendered, and
* what numbering scheme is used for inline citations.

Keeping this isolated from :class:`RAGService` means the prompt format
can evolve (truncation, dedupe, language tags, …) without touching the
orchestration layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from app.schemas.search import RetrievedChunk


@dataclass(frozen=True)
class HistoryTurn:
    """One rendered turn from the conversation history.

    ``role`` is "user" or "assistant"; ``content`` is the (already
    truncated, if applicable) text to forward to the LLM.
    """

    role: str
    content: str


class ContextBuilder:
    """Render retrieved chunks + history into a context block for the LLM."""

    HISTORY_HEADER = "CONVERSATION HISTORY"
    SOURCES_HEADER = "SOURCES"
    QUESTION_HEADER = "QUESTION"

    def build_context(
        self,
        chunks: Sequence[RetrievedChunk],
        *,
        max_chunks: int | None = None,
    ) -> str:
        """Render ``chunks`` as a numbered ``[SOURCE n]`` block."""
        if max_chunks is not None:
            chunks = list(chunks[:max_chunks])
        else:
            chunks = list(chunks)

        if not chunks:
            return ""

        parts: List[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            parts.append(self._render_source(idx, chunk))
        return "\n\n".join(parts)

    @staticmethod
    def render_history(turns: Sequence[HistoryTurn]) -> str:
        """Render a list of history turns as a single text block.

        Returns an empty string when ``turns`` is empty. Order is
        preserved (oldest first).
        """
        if not turns:
            return ""
        lines: List[str] = []
        for turn in turns:
            role = "User" if turn.role == "user" else "Assistant"
            content = turn.content.strip()
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def build_user_prompt(
        self,
        query: str,
        context: str,
        *,
        history: Sequence[HistoryTurn] = (),
    ) -> str:
        """Wrap the user question, retrieval context, and history into a
        single user message.

        Backwards-compatible: when ``history`` is empty, the prompt is
        the legacy ``Sources:\\n...\\n\\nQuestion:\\n<query>`` shape so
        existing one-shot callers see no change.

        When ``history`` is non-empty, the layout becomes:

            CONVERSATION HISTORY
            <turns>

            SOURCES
            [SOURCE 1]
            ...

            QUESTION
            <query>
        """
        history_block = self.render_history(history)

        # Legacy (no-history) layout — preserves the old label
        # "Sources:" used by existing tests / prompts.
        if not history_block:
            if context:
                return (
                    "Sources:\n"
                    f"{context}\n\n"
                    "Question:\n"
                    f"{query.strip()}"
                )
            return (
                "No relevant sources were found in your documents.\n\n"
                "Question:\n"
                f"{query.strip()}"
            )

        # History-aware layout.
        sections: List[str] = []
        sections.append(f"{self.HISTORY_HEADER}:\n{history_block}")
        if context:
            sections.append(f"{self.SOURCES_HEADER}:\n{context}")
        else:
            sections.append(
                "No relevant sources were found in your documents."
            )
        sections.append(f"{self.QUESTION_HEADER}:\n{query.strip()}")
        return "\n\n".join(sections)

    # ----- internals -----

    @staticmethod
    def _render_source(index: int, chunk: RetrievedChunk) -> str:
        """Render a single chunk as ``[SOURCE n]`` followed by its text."""
        text = (chunk.text or "").strip()
        if not text:
            # Defensive — never emit an empty source block; the model
            # would treat it as a missing citation.
            text = "(empty source excerpt)"
        return f"[SOURCE {index}]\n{text}"


__all__ = ["ContextBuilder", "HistoryTurn"]
