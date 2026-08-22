"""ChatSession and ChatMessage ORM models.

A `ChatSession` is a conversation owned by a single user. Each
`ChatMessage` belongs to one session and carries a role-tagged payload
(typically fed to/from an LLM).

`ChatMessageSource` persists the citations used to ground each
assistant answer so they survive outside of retrieval calls.

ChatSessions MAY optionally belong to a :class:`Course` (Phase 6B).
``course_id`` is nullable so existing sessions remain valid.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.models.enums import ChatRole

if TYPE_CHECKING:
    from app.db.models.course import Course
    from app.db.models.user import User


class ChatSession(UUIDPKMixin, TimestampMixin, Base):
    """A conversation thread owned by a user."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
        # Common course-scoped listing: "sessions in a course, newest first".
        Index("ix_chat_sessions_course_updated", "course_id", "updated_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(length=255), nullable=False, default="New chat"
    )

    # Course link (Phase 6B). Optional so sessions can exist outside
    # any course — backward compatibility with all rows created
    # before Phase 6B.
    course_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Document link (Phase 6E). Optional so sessions can be general
    # or scoped to a specific document.
    document_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    course: Mapped[Optional["Course"]] = relationship(
        "Course", back_populates="chat_sessions"
    )
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<ChatSession id={self.id} title={self.title!r} "
            f"course={self.course_id}>"
        )


class ChatMessage(UUIDPKMixin, TimestampMixin, Base):
    """A single message inside a chat session.

    Inherits `TimestampMixin` for `created_at`/`updated_at`. We don't
    auto-update `updated_at` on edit because chat history is typically
    append-only; the column stays available for moderation tools.
    """

    __tablename__ = "chat_messages"
    __table_args__ = (
        # Common query: list messages in a session, ordered by time.
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[ChatRole] = mapped_column(
        String(length=16),
        nullable=False,
        default=ChatRole.USER,
        server_default=ChatRole.USER.value,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )
    sources: Mapped[List["ChatMessageSource"]] = relationship(
        "ChatMessageSource",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="ChatMessageSource.position",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ChatMessage id={self.id} role={self.role} session={self.session_id}>"


class ChatMessageSource(UUIDPKMixin, TimestampMixin, Base):
    """A single citation attached to an assistant message.

    Persists the (document_id, chunk_id, page/slide, score) tuple that
    was used to ground the message so the conversation view can render
    citations without rerunning retrieval.
    """

    __tablename__ = "chat_message_sources"
    __table_args__ = (
        Index(
            "ix_chat_message_sources_message_position",
            "message_id",
            "position",
        ),
    )

    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(String(length=128), nullable=False)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="1-based citation index in the prompt."
    )
    page_number: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="1-based page number, when known."
    )
    slide_number: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="1-based slide number, when known."
    )
    score: Mapped[Optional[float]] = mapped_column(
        Numeric(precision=8, scale=6), nullable=True,
    )
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    message: Mapped["ChatMessage"] = relationship(
        "ChatMessage", back_populates="sources"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<ChatMessageSource id={self.id} message={self.message_id} "
            f"doc={self.document_id} pos={self.position}>"
        )
