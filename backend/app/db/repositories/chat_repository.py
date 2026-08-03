"""Chat repositories.

`ChatSessionRepository` and `ChatMessageRepository` cover conversations
and individual messages. Splitting them keeps each surface focused.
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import ChatMessage, ChatSession
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
    ) -> Sequence[ChatSession]:
        """List chat sessions owned by a user, most recently active first."""
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def rename(self, session_obj: ChatSession, *, title: str) -> ChatSession:
        """Update a session's title."""
        return await self.update(session_obj, {"title": title})


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Async repository for :class:`app.db.models.chat.ChatMessage`."""

    model = ChatMessage

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_for_session(
        self,
        session_id: UUID | str,
        *,
        skip: int = 0,
        limit: int = 1000,
    ) -> Sequence[ChatMessage]:
        """List messages in chronological order for a session."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
