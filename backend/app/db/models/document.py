"""Document ORM model.

A user-uploaded file (PDF, DOCX, etc.) tracked before any parsing or
indexing happens. `storage_path` is opaque to the model layer — the
`storage` package handles the actual persistence backend.

Documents MAY optionally belong to a :class:`Course` (Phase 6B).
The course link is independent of ownership: a document always
belongs to one user, and may additionally be grouped under exactly
one of that user's courses. ``course_id`` is nullable so existing
documents remain valid.

Phase 6C adds structured academic classification:

* ``document_type`` — controlled :class:`DocumentType` enum value.
  Nullable on the column so rows created before Phase 6C stay valid
  (``NULL`` is the legacy state, not an invented classification).
* ``document_metadata`` — a JSONB blob of optional academic metadata
  (author, subject, semester, academic_year, tags) validated by
  :class:`app.schemas.document.DocumentMetadataPayload`.

Both fields are intentionally independent of the existing ``file_type``
(storage format suffix), ``course_id`` (course link), and
``upload_status`` (pipeline state).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.models.enums import DocumentType, DocumentUploadStatus

if TYPE_CHECKING:
    from app.db.models.course import Course
    from app.db.models.user import User


# ``JSON`` works on every supported dialect (PostgreSQL falls back to
# ``JSON`` when the bound dialect is SQLite). Alembic hand-issues a
# ``JSONB`` column in the migration so production Postgres benefits
# from the binary representation; this dialect-aware alias keeps
# ``create_all`` working in the SQLite test harness.
_JsonType: Any = JSONB().with_variant(JSON(), "sqlite")


class Document(UUIDPKMixin, TimestampMixin, Base):
    """A file uploaded by a user for later processing."""

    __tablename__ = "documents"
    __table_args__ = (
        # Composite index keeps the common "latest docs per owner" query fast.
        Index("ix_documents_owner_created", "owner_id", "created_at"),
        # Common course-scoped listing: "docs in a course, newest first".
        Index("ix_documents_course_created", "course_id", "created_at"),
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

    # Course link (Phase 6B). Optional so documents can exist outside
    # any course — backward compatibility with all rows created
    # before Phase 6B.
    course_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ---- Phase 6C: structured academic classification ----

    # Controlled enum. Stored as a short ``VARCHAR`` so adding new
    # values is non-breaking: existing rows that pre-date Phase 6C
    # remain ``NULL`` (the canonical "uncategorised" state).
    document_type: Mapped[Optional[DocumentType]] = mapped_column(
        String(length=32),
        nullable=True,
        index=True,
    )

    # Structured academic metadata. JSONB on Postgres (``create_all``
    # uses JSON on SQLite — see ``_JsonType`` above).
    document_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        _JsonType,
        nullable=True,
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="documents")
    course: Mapped[Optional["Course"]] = relationship(
        "Course", back_populates="documents"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<Document id={self.id} filename={self.filename!r} "
            f"type={self.document_type} status={self.upload_status} "
            f"course={self.course_id}>"
        )
