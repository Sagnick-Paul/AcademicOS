"""User ORM model.

Represents a registered AcademicOS user. The `documents` and
`chat_sessions` relationships make it the aggregate root for
user-scoped data.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.db.models.chat import ChatSession
    from app.db.models.document import Document


class User(UUIDPKMixin, TimestampMixin, Base):
    """A registered user of AcademicOS."""

    __tablename__ = "users"

    # Profile
    full_name: Mapped[str] = mapped_column(
        String(length=255), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(length=320),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(length=255), nullable=False
    )

    # Account state
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Relationships
    # `cascade="all, delete-orphan"` enforces ownership semantics:
    # deleting a user removes their documents and chat sessions.
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User id={self.id} email={self.email!r}>"
