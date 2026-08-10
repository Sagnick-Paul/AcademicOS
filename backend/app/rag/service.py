"""RAG orchestration service.

Owns the end-to-end Q&A flow:

    user query (+ optional conversation history)
        │
        ▼
    RetrievalService.retrieve (semantic | hybrid, owner-scoped)
        │
        ├── no chunks  ──► NoRelevantContextError
        │
        ▼
    ContextBuilder.build_context + render_history
        │
        ▼
    LLMProvider.generate (system: grounding prompt, user: history + sources + question)
        │
        ▼
    RAGAnswer  (text + sources + usage)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence
from uuid import UUID

from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from app.rag.context_builder import ContextBuilder, HistoryTurn
from app.rag.exceptions import NoRelevantContextError
from app.rag.grounding_prompt import GROUNDING_SYSTEM_PROMPT
from app.schemas.search import RetrievedChunk
from app.services.retrieval_service import RetrievalService

logger = get_logger(__name__)


@dataclass
class ChatSource:
    """A single citation surfaced in a chat response."""

    index: int            # 1-based index, matches "[SOURCE n]" in prompt
    chunk_id: str
    document_id: Optional[UUID]
    document_title: Optional[str]  # set by endpoint; service leaves None
    page_number: Optional[int]
    chunk_index: int
    score: float
    snippet: str          # short preview of the chunk text


@dataclass
class RAGAnswer:
    """The full output of a single Q&A turn."""

    answer: str
    sources: List[ChatSource]
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    retrieval_mode: str = "semantic"


class RAGService:
    """Coordinates retrieval + LLM to answer a question grounded in docs."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_provider: BaseLLMProvider,
        *,
        context_builder: Optional[ContextBuilder] = None,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.llm_provider = llm_provider
        self.context_builder = context_builder or ContextBuilder()

    async def answer_question(
        self,
        *,
        query: str,
        owner_id: UUID,
        document_id: Optional[UUID] = None,
        mode: str = "semantic",
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
        conversation_history: Optional[Sequence[HistoryTurn]] = None,
    ) -> RAGAnswer:
        """Retrieve, build a prompt, call the LLM, return answer + citations.

        Parameters
        ----------
        conversation_history:
            Optional list of :class:`HistoryTurn` items to inject
            into the prompt. The grounding prompt and document sources
            remain authoritative; history is only used by the model
            to disambiguate the current question.

        Raises:
            NoRelevantContextError: retrieval returned zero chunks. The
                endpoint layer translates this into a clean, model-free
                response.
            LLMError: any LLM-side failure (auth, quota, network, etc.).
        """
        chunks = await self.retrieval_service.retrieve(
            query=query,
            owner_id=owner_id,
            limit=top_k,
            score_threshold=score_threshold,
            document_id=document_id,
            mode=mode,
        )

        if not chunks:
            raise NoRelevantContextError(query)

        context_block = self.context_builder.build_context(chunks)
        history = list(conversation_history or [])
        user_prompt = self.context_builder.build_user_prompt(
            query, context_block, history=history,
        )

        llm_request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=GROUNDING_SYSTEM_PROMPT),
                LLMMessage(role="user", content=user_prompt),
            ],
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        logger.info(
            "rag.answer owner=%s doc=%s mode=%s chunks=%s history=%s",
            owner_id,
            document_id,
            mode,
            len(chunks),
            len(history),
        )

        llm_response: LLMResponse = await self.llm_provider.generate(llm_request)

        sources = self._build_sources(chunks)
        return RAGAnswer(
            answer=llm_response.text,
            sources=sources,
            model=llm_response.model,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            retrieval_mode=mode,
        )

    # ----- helpers -----

    @staticmethod
    def _build_sources(chunks: List[RetrievedChunk]) -> List[ChatSource]:
        """Turn retrieved chunks into numbered citations."""
        sources: List[ChatSource] = []
        for idx, chunk in enumerate(chunks, start=1):
            snippet = (chunk.text or "").strip()
            if len(snippet) > 280:
                snippet = snippet[:277].rstrip() + "..."
            sources.append(
                ChatSource(
                    index=idx,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_title=None,  # endpoint can fill this in if it wants
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    score=chunk.score,
                    snippet=snippet,
                )
            )
        return sources


__all__ = ["ChatSource", "RAGAnswer", "RAGService"]