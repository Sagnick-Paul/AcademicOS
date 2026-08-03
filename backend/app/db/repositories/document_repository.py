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
from app.db.models.enums import DocumentUploadStatus
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
    ) -> Sequence[Document]:
        """List documents belonging to a specific user, newest first."""
        stmt = (
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
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
