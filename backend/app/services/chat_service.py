"""Chat / conversation orchestration service.

Responsibilities (kept out of the endpoint layer):

* session lifecycle (create, list, get, delete) with ownership checks,
* persisting user and assistant messages,
* persisting per-citation metadata for every assistant answer,
* loading a controlled slice of conversation history,
* calling the RAG service,
* transaction boundaries so a failed LLM call never leaves a fake
  assistant message behind.

Architecture:

    API
     ↓
    ChatService
     ├── ChatSessionRepository
     ├── ChatMessageRepository
     ├── ChatMessageSourceRepository
     └── RAGService
           ├── RetrievalService
           ├── ContextBuilder
           └── LLMProvider
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence
from uuid import UUID

# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.chat import ChatMessage, ChatMessageSource, ChatSession
from app.db.models.document import Document
from app.db.models.enums import ChatRole
from app.db.models.user import User
from app.db.repositories.chat_repository import (
    ChatMessageRepository,
    ChatMessageSourceRepository,
    ChatSessionRepository,
)
from app.db.repositories.document_repository import DocumentRepository
from app.llm.exceptions import LLMError
from app.rag.context_builder import HistoryTurn
from app.rag.exceptions import NoRelevantContextError
from app.rag.service import ChatSource, RAGAnswer, RAGService
from app.services.chat_exceptions import (
    ChatMessageEmptyError,
    ChatSessionNotFoundError,
)

logger = logging.getLogger(__name__)


_NO_CONTEXT_ANSWER = (
    "I cannot answer this based on the provided documents."
)


@dataclass
class ChatTurnResult:
    """The result of a single :meth:`ChatService.send_message` call."""

    user_message: ChatMessage
    assistant_message: ChatMessage
    sources: List[ChatSource]
    rag_answer: RAGAnswer


class ChatService:
    """Conversational RAG orchestration.

    The service never raises ``HTTPException`` — only domain exceptions
    documented in :mod:`app.services.chat_exceptions` and
    :mod:`app.llm.exceptions`. The endpoint layer is responsible for
    translating them into HTTP responses.
    """

    def __init__(
        self,
        session: AsyncSession,
        rag_service: RAGService,
        *,
        session_repo: Optional[ChatSessionRepository] = None,
        message_repo: Optional[ChatMessageRepository] = None,
        source_repo: Optional[ChatMessageSourceRepository] = None,
        document_repo: Optional[DocumentRepository] = None,
    ) -> None:
        self.session = session
        self.rag_service = rag_service
        self.session_repo = session_repo or ChatSessionRepository(session)
        self.message_repo = message_repo or ChatMessageRepository(session)
        self.source_repo = source_repo or ChatMessageSourceRepository(session)
        self.document_repo = document_repo or DocumentRepository(session)

    # ------------------------------------------------------------------ #
    #  Session lifecycle                                                  #
    # ------------------------------------------------------------------ #

    async def create_session(
        self,
        *,
        owner: User,
        title: Optional[str] = None,
        initial_query: Optional[str] = None,
    ) -> ChatSession:
        """Create a new chat session for ``owner``.

        If ``initial_query`` is supplied, the session is created with
        a title derived from the first message and the message itself
        is persisted as a user message (no assistant reply yet — the
        caller is expected to follow up with ``send_message``).
        """
        if initial_query is not None and not initial_query.strip():
            raise ChatMessageEmptyError()

        # Treat the schema default ("New chat") as "no explicit title" so
        # a follow-up ``initial_query`` is always reflected in the title.
        derived_title = title
        if derived_title is None or derived_title == "New chat":
            if initial_query is not None:
                derived_title = self._derive_title(initial_query)
            else:
                derived_title = "New chat"
        if derived_title is None:
            derived_title = "New chat"

        session = ChatSession(
            user_id=owner.id,
            title=derived_title,
        )
        session = await self.session_repo.create(session)
        await self.session.commit()

        if initial_query is not None:
            # Persist the opener message but do NOT call the LLM —
            # that is the caller's job in the next request.
            msg = ChatMessage(
                session_id=session.id,
                role=ChatRole.USER,
                content=initial_query.strip(),
            )
            await self.message_repo.create(msg)
            await self.session.commit()

        logger.info(
            "chat.session.created id=%s user=%s", session.id, owner.id,
        )
        return session

    async def list_user_sessions(
        self,
        *,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ChatSession]:
        """List sessions owned by ``owner_id``, newest first."""
        return await self.session_repo.list_for_user(
            owner_id, skip=skip, limit=limit,
        )

    async def get_session_for_user(
        self,
        *,
        session_id: UUID,
        owner_id: UUID,
    ) -> ChatSession:
        """Return a session, or raise :class:`ChatSessionNotFoundError`.

        ``ChatSessionNotFoundError`` is raised for both "missing" and
        "owned by someone else" so callers can safely treat the
        exception as a 404 with no information leak.
        """
        sess = await self.session_repo.get_by_id(session_id)
        if sess is None or sess.user_id != owner_id:
            raise ChatSessionNotFoundError(session_id)
        return sess

    async def delete_session(
        self,
        *,
        session_id: UUID,
        owner_id: UUID,
    ) -> None:
        """Delete a session (and its messages, via CASCADE)."""
        sess = await self.get_session_for_user(
            session_id=session_id, owner_id=owner_id,
        )
        await self.session_repo.delete(sess)
        await self.session.commit()
        logger.info(
            "chat.session.deleted id=%s user=%s", session_id, owner_id,
        )

    async def get_session_with_messages(
        self,
        *,
        session_id: UUID,
        owner_id: UUID,
    ) -> ChatSession:
        """Return a session with its messages eagerly loaded."""
        sess = await self.get_session_for_user(
            session_id=session_id, owner_id=owner_id,
        )
        # Force-load messages via the repository so the endpoint can
        # serialise them without an extra round-trip. Reassign the
        # ``messages`` attribute on the session so downstream code
        # sees the freshly loaded rows (the original list may be
        # stale from the identity-map cache).
        messages = list(await self.message_repo.list_for_session(sess.id))
        sess.messages = messages  # type: ignore[assignment]
        return sess

    # ------------------------------------------------------------------ #
    #  Conversation message send                                           #
    # ------------------------------------------------------------------ #

    async def send_message(
        self,
        *,
        session_id: UUID,
        owner_id: UUID,
        query: str,
        document_id: Optional[UUID] = None,
        mode: str = "semantic",
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> ChatTurnResult:
        """Persist a user question, call RAG, persist the assistant answer.

        Failure semantics:

        * If the session is missing or owned by another user → raise
          :class:`ChatSessionNotFoundError` (no state changes).
        * If ``document_id`` does not belong to the user → raise
          :class:`DocumentNotFoundError` (no state changes).
        * If the RAG call raises :class:`NoRelevantContextError`,
          persist a polite refusal as the assistant message with
          empty sources — the conversation is still consistent.
        * If the LLM raises any :class:`LLMError` subclass, roll back
          the user message insert so the conversation stays clean.
        """
        if not query or not query.strip():
            raise ChatMessageEmptyError()

        # 1. Validate session ownership FIRST. No DB writes yet.
        sess = await self.get_session_for_user(
            session_id=session_id, owner_id=owner_id,
        )

        # 2. Validate document ownership if specified. Done before any
        #    insert so a 404 path does not leave the user message
        #    persisted.
        if document_id is not None:
            await self._authorize_document(document_id, owner_id)

        # 3. Load recent history BEFORE writing the new user message,
        #    so the new turn is not echoed back into the prompt.
        history = await self._load_history(sess.id)

        # 4. Persist the user message. NOTE: do NOT commit yet — the
        #    user insert is part of the same transaction as the assistant
        #    message + sources that follow. Committing now would make a
        #    later LLMError rollback a no-op and leak a half-written turn.
        user_msg = ChatMessage(
            session_id=sess.id,
            role=ChatRole.USER,
            content=query.strip(),
        )
        await self.message_repo.create(user_msg)

        # 5. Call RAG. Any LLMError must roll back BOTH the user insert
        #    and any sources already staged in this transaction.
        try:
            rag_answer = await self.rag_service.answer_question(
                query=query,
                owner_id=owner_id,
                document_id=document_id,
                mode=mode,
                top_k=top_k,
                score_threshold=score_threshold,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                conversation_history=history,
            )
            assistant_text = rag_answer.answer
            rag_sources: List[ChatSource] = list(rag_answer.sources)
        except NoRelevantContextError:
            assistant_text = _NO_CONTEXT_ANSWER
            rag_sources = []
        except LLMError:
            # Roll back the user message (and any pending source rows) so
            # the conversation is not left half-written. The caller will
            # see the original LLMError.
            await self.session.rollback()
            raise

        # 6. Persist the assistant message + its sources.
        assistant_msg = ChatMessage(
            session_id=sess.id,
            role=ChatRole.ASSISTANT,
            content=assistant_text,
        )
        await self.message_repo.create(assistant_msg)
        await self.session.flush()  # need assistant_msg.id for sources

        if rag_sources:
            source_rows: List[ChatMessageSource] = []
            for src in rag_sources:
                # Only persist citations whose chunk belongs to a real
                # document the user owns. Defensive — retrieval
                # already enforced ownership, but a future regression
                # here would silently leak.
                if src.document_id is None:
                    continue
                if not await self._user_owns_document(
                    src.document_id, owner_id,
                ):
                    continue
                source_rows.append(
                    ChatMessageSource(
                        message_id=assistant_msg.id,
                        document_id=src.document_id,
                        chunk_id=src.chunk_id,
                        position=src.index,
                        page_number=src.page_number,
                        score=src.score,
                        snippet=src.snippet,
                    )
                )
            await self.source_repo.create_many(source_rows)

        # 7. Bump session.updated_at so list ordering reflects activity.
        await self.session_repo.update(
            sess, {"title": sess.title},
        )
        await self.session.commit()

        logger.info(
            "chat.message.persisted session=%s user_msg=%s "
            "assistant_msg=%s sources=%s",
            sess.id, user_msg.id, assistant_msg.id, len(rag_sources),
        )

        return ChatTurnResult(
            user_message=user_msg,
            assistant_message=assistant_msg,
            sources=rag_sources,
            rag_answer=RAGAnswer(
                answer=assistant_text,
                sources=rag_sources,
                model=(
                    getattr(rag_answer, "model", "unknown")
                    if "rag_answer" in locals()
                    else "unknown"
                ),
                prompt_tokens=None,
                completion_tokens=None,
                retrieval_mode=mode,
            ),
        )

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    async def _load_history(
        self,
        session_id: UUID,
    ) -> List[HistoryTurn]:
        """Build a bounded list of history turns for the LLM prompt.

        Reads ``settings.CHAT_HISTORY_MESSAGE_LIMIT`` recent messages
        and applies per-message and total character caps.
        """
        limit = settings.CHAT_HISTORY_MESSAGE_LIMIT
        per_msg_chars = settings.CHAT_HISTORY_MESSAGE_CHAR_LIMIT
        total_chars = settings.CHAT_HISTORY_TOTAL_CHAR_LIMIT

        rows = await self.message_repo.list_recent_for_session(
            session_id, limit=limit,
        )
        # ``list_recent_for_session`` already returns the rows in
        # chronological order. We render them top-to-bottom for the LLM
        # but want the most-recent turns to stay intact when the total
        # character budget runs out. So we trim from the FRONT of the
        # list if and only if the total budget is exceeded.
        per_msg_chars = settings.CHAT_HISTORY_MESSAGE_CHAR_LIMIT
        total_chars = settings.CHAT_HISTORY_TOTAL_CHAR_LIMIT

        # First pass: per-message truncation + drop empties.
        prepared: List[HistoryTurn] = []
        for row in rows:
            content = (row.content or "").strip()
            if not content:
                continue
            if len(content) > per_msg_chars:
                content = content[: per_msg_chars - 3].rstrip() + "..."
            # The ``role`` column may round-trip as either a ``ChatRole``
            # enum or a plain string depending on backend/transport,
            # so coerce defensively.
            role_str = (
                row.role.value
                if hasattr(row.role, "value")
                else str(row.role)
            )
            prepared.append(HistoryTurn(role=role_str, content=content))

        # Second pass: enforce total char budget by dropping the
        # OLDEST prepared turns until we fit. This guarantees the most
        # recent history is preserved.
        while prepared and sum(len(t.content) for t in prepared) > total_chars:
            prepared.pop(0)

        return prepared

    async def _authorize_document(
        self,
        document_id: UUID,
        owner_id: UUID,
    ) -> Document:
        """Raise :class:`DocumentNotFoundError` for foreign or missing docs."""
        from app.services.exceptions import DocumentNotFoundError

        doc = await self.document_repo.get_by_id(document_id)
        if doc is None or doc.owner_id != owner_id:
            raise DocumentNotFoundError(document_id)
        return doc

    async def _user_owns_document(
        self,
        document_id: UUID,
        owner_id: UUID,
    ) -> bool:
        """Cheap boolean ownership check used when persisting sources."""
        doc = await self.document_repo.get_by_id(document_id)
        return doc is not None and doc.owner_id == owner_id

    @staticmethod
    def _derive_title(query: str) -> str:
        """Deterministically derive a short title from the first query.

        Cheap and explainable: takes the first words, capitalises them,
        and truncates to ``title_field`` length. Never calls the LLM.
        """
        words = re.findall(r"[A-Za-z0-9']+", query)
        if not words:
            return "New chat"
        # Title-case; preserve consecutive word count up to a sensible cap.
        head = " ".join(w.capitalize() for w in words[:8])
        return head[:255] or "New chat"


__all__ = ["ChatService", "ChatTurnResult"]