"""Document repository.

Per-owner listing and status mutations live here. Storage I/O is the
job of `app.storage`, not this module.
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.enums import DocumentType, DocumentUploadStatus
from app.db.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Async repository for :class:`app.db.models.document.Document`."""

    model = Document

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ---------- Lookups ----------

    async def list_for_owner(
        self,
        owner_id: UUID | str,
        *,
        skip: int = 0,
        limit: int = 100,
        course_id: UUID | str | None = None,
        document_type: DocumentType | None = None,
    ) -> Sequence[Document]:
        """List documents belonging to a specific user, newest first.

        When ``course_id`` is provided, results are restricted to that
        course. When ``document_type`` is provided (Phase 6C), results
        are restricted to that academic classification. Both filters
        compose: supplying both returns the intersection. Supplying
        neither preserves the legacy behaviour.

        The caller is responsible for verifying that the course
        belongs to ``owner_id`` — this method does not check.
        """
        stmt = select(Document).where(Document.owner_id == owner_id)
        if course_id is not None:
            stmt = stmt.where(Document.course_id == course_id)
        if document_type is not None:
            # Compare against the underlying string so the row's
            # ``NULL`` (legacy rows) does not match.
            stmt = stmt.where(Document.document_type == document_type)
        stmt = (
            stmt.order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_status(
        self,
        status: DocumentUploadStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        """List documents currently in a given upload status."""
        stmt = (
            select(Document)
            .where(Document.upload_status == status)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ---------- Mutators ----------

    async def set_status(
        self,
        document: Document,
        status: DocumentUploadStatus,
    ) -> Document:
        """Transition a document to a new upload status."""
        return await self.update(document, {"upload_status": status})

    async def set_course(
        self,
        document: Document,
        course_id: UUID | str | None,
    ) -> Document:
        """Assign (or clear) the document's course link.

        ``None`` unlinks the document. Caller must verify that the
        course belongs to the document's owner.
        """
        return await self.update(document, {"course_id": course_id})

    async def set_classification(
        self,
        document: Document,
        *,
        document_type: DocumentType | None,
        document_metadata: dict | None,
    ) -> Document:
        """Persist the Phase 6C classification fields atomically.

        Both fields are written in a single UPDATE — convenience for
        callers that have already resolved the partial-update
        semantics and need both. Use :meth:`update` directly when
        only one field changes.
        """
        return await self.update(
            document,
            {
                "document_type": document_type,
                "document_metadata": document_metadata,
            },
        )
