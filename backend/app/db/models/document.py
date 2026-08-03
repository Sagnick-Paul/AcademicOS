"""Document ORM model.

A user-uploaded file (PDF, DOCX, etc.) tracked before any parsing or
indexing happens. `storage_path` is opaque to the model layer — the
`storage` package handles the actual persistence backend.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.models.enums import DocumentUploadStatus

if TYPE_CHECKING:
    from app.db.models.user import User


class Document(UUIDPKMixin, TimestampMixin, Base):
    """A file uploaded by a user for later processing."""

    __tablename__ = "documents"
    __table_args__ = (
        # Composite index keeps the common "latest docs per owner" query fast.
        Index("ix_documents_owner_created", "owner_id", "created_at"),
    )

    # Ownership
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File metadata
    filename: Mapped[str] = mapped_column(
        String(length=512), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(
        String(length=512), nullable=False
    )
    file_type: Mapped[str] = mapped_column(
        String(length=64), nullable=False, index=True
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    storage_path: Mapped[str] = mapped_column(
        String(length=1024), nullable=False
    )
    upload_status: Mapped[DocumentUploadStatus] = mapped_column(
        String(length=32),
        nullable=False,
        default=DocumentUploadStatus.PENDING,
        server_default=DocumentUploadStatus.PENDING.value,
        index=True,
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="documents")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Document id={self.id} filename={self.filename!r} status={self.upload_status}>"
