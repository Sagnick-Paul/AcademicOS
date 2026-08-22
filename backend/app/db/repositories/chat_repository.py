"""Chat repositories.

`ChatSessionRepository`, `ChatMessageRepository`, and
`ChatMessageSourceRepository` cover conversations, individual messages,
and the per-citation metadata that grounds each assistant answer.

Splitting them keeps each surface focused and lets the service layer
compose the three without juggling module-level state.
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import ChatMessage, ChatMessageSource, ChatSession
from app.db.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    """Async repository for :class:`app.db.models.chat.ChatSession`."""

    model = ChatSession

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_for_user(
        self,
        user_id: UUID | str,
        *,
        skip: int = 0,
        limit: int = 100,
        course_id: UUID | str | None = None,
    ) -> Sequence[ChatSession]:
        """List chat sessions owned by a user, most recently active first.

        When ``course_id`` is provided, results are restricted to that
        course. The caller is responsible for verifying that the
        course belongs to ``user_id`` — this method does not check.
        """
        stmt = select(ChatSession).where(ChatSession.user_id == user_id)
        if course_id is not None:
            stmt = stmt.where(ChatSession.course_id == course_id)
        stmt = (
            stmt.order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def rename(self, session_obj: ChatSession, *, title: str) -> ChatSession:
        """Update a session's title."""
        return await self.update(session_obj, {"title": title})

    async def set_course(
        self,
        session_obj: ChatSession,
        course_id: UUID | str | None,
    ) -> ChatSession:
        """Assign (or clear) the session's course link.

        ``None`` unlinks the session. Caller must verify that the
        course belongs to the session's owner.
        """
        return await self.update(session_obj, {"course_id": course_id})


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Async repository for :class:`app.db.models.chat.ChatMessage`."""

    model = ChatMessage

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def _is_sqlite(self) -> bool:
        """True when the bound backend is SQLite."""
        return self.session.get_bind().dialect.name == "sqlite"

    def _tiebreaker(self, direction: str):
        """Dialect-aware secondary ORDER BY key.

        * SQLite → the implicit ``rowid`` (monotonic with insertion
          order). This is the only reliable tiebreaker for SQLite's
          second-precision ``CURRENT_TIMESTAMP`` under tight INSERT
          loops. UUIDs are random so they don't work.
        * Postgres / other → ``id`` (random but stable within a
          single query — Postgres's microsecond ``now()`` already
          makes the tiebreaker unused in practice).
        """
        if direction not in ("asc", "desc"):
            raise ValueError(
                f"direction must be 'asc' or 'desc', got {direction!r}",
            )
        col = literal_column("rowid") if self._is_sqlite() else ChatMessage.id
        return col.asc() if direction == "asc" else col.desc()

    def _order_clauses(self, primary_direction: str):
        """Build the (created_at, tiebreaker) ORDER BY pair."""
        if primary_direction == "asc":
            return (ChatMessage.created_at.asc(), self._tiebreaker("asc"))
        if primary_direction == "desc":
            return (ChatMessage.created_at.desc(), self._tiebreaker("desc"))
        raise ValueError(
            f"primary_direction must be 'asc' or 'desc', got {primary_direction!r}",
        )

    async def list_for_session(
        self,
        session_id: UUID | str,
        *,
        skip: int = 0,
        limit: int = 1000,
    ) -> Sequence[ChatMessage]:
        """List messages in chronological order for a session.

        Ordering is ``(created_at ASC, <dialect-tiebreaker> ASC)``.
        On SQLite the tiebreaker is the implicit ``rowid``, which is
        strictly monotonic with insertion order. Without it the
        LIMIT/OFFSET slice and the *last element of the slice* would
        both become non-deterministic when many rows share the same
        ``CURRENT_TIMESTAMP`` second (SQLite's default precision).
        """
        primary, tie = self._order_clauses("asc")
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(primary, tie)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_recent_for_session(
        self,
        session_id: UUID | str,
        *,
        limit: int,
    ) -> Sequence[ChatMessage]:
        """Return the most recent N messages for a session, oldest first.

        Used by the chat service to slice a controlled conversation
        history for the LLM prompt. Oldest-first ordering keeps the
        prompt natural to read.

        Ordering is ``(created_at DESC, tiebreaker DESC)`` for the
        inner ``LIMIT`` and ``(created_at ASC, tiebreaker ASC)`` for
        the outer re-order. The tiebreaker is essential when
        ``created_at`` ties — which SQLite's second-precision
        ``CURRENT_TIMESTAMP`` causes under tight INSERT loops. On
        SQLite the tiebreaker is the implicit ``rowid`` (monotonic);
        elsewhere it falls back to the primary-key ``id``.
        """
        if limit <= 0:
            return []
        primary_desc, tie_desc = self._order_clauses("desc")
        primary_asc, tie_asc = self._order_clauses("asc")
        # Subquery: latest N ids by (created_at DESC, tiebreaker DESC).
        id_stmt = (
            select(ChatMessage.id)
            .where(ChatMessage.session_id == session_id)
            .order_by(primary_desc, tie_desc)
            .limit(limit)
        )
        # Order the chosen rows back into chronological order.
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.id.in_(id_stmt.subquery()))
            .order_by(primary_asc, tie_asc)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class ChatMessageSourceRepository(BaseRepository[ChatMessageSource]):
    """Async repository for :class:`app.db.models.chat.ChatMessageSource`."""

    model = ChatMessageSource

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_for_message(
        self, message_id: UUID | str,
    ) -> Sequence[ChatMessageSource]:
        """List citations for a single message, ordered by position."""
        stmt = (
            select(ChatMessageSource)
            .where(ChatMessageSource.message_id == message_id)
            .order_by(ChatMessageSource.position.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_many(
        self,
        sources: Sequence[ChatMessageSource],
    ) -> Sequence[ChatMessageSource]:
        """Bulk-insert a list of source rows. Flushes once."""
        for src in sources:
            self.session.add(src)
        if sources:
            await self.session.flush()
        return sources


__all__ = [
    "ChatMessageRepository",
    "ChatMessageSourceRepository",
    "ChatSessionRepository",
]