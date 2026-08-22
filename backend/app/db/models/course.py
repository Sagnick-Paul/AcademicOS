"""Course ORM model.

A `Course` is a user-owned academic container — the next layer above
`Document`. In Phase 6A a course has no children yet (the
`Document.course_id` link belongs to later subphases). What we ship
here is the user → course relationship and the per-owner uniqueness
rule on `name`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.db.models.chat import ChatSession
    from app.db.models.document import Document
    from app.db.models.user import User


class Course(UUIDPKMixin, TimestampMixin, Base):
    """An academic course owned by a single user.

    A course groups documents and chat sessions in later phases; here
    it exists on its own as the foundational entity users will organise
    their work around. `name` is required; `code` and `description` are
    optional. The `(owner_id, name)` pair is unique — two different
    users can both have a course called "Signals & Systems", but a
    single user cannot have two courses with the same name.
    """

    __tablename__ = "courses"
    __table_args__ = (
        # Per-owner uniqueness on `name`. The dedicated index name lets
        # Alembic downgrade drop the constraint deterministically.
        UniqueConstraint("owner_id", "name", name="uq_courses_owner_name"),
        # Common query: list a user's courses by most recent activity.
        Index("ix_courses_owner_updated", "owner_id", "updated_at"),
    )

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="courses",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="course",
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="course",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Course id={self.id} owner={self.owner_id} name={self.name!r}>"


__all__: list[str] = ["Course"]
