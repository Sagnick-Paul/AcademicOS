"""Document service.

Owns:

* validating uploads (size, content, type)
* coordinating the storage layer and the ORM model
* enforcing per-user ownership on every read / delete

The endpoint layer is thin — it calls the service, translates domain
exceptions into HTTP responses, and commits the session. No business
logic lives outside this module (and the storage package beneath it).
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.document import Document
from app.db.models.enums import DocumentUploadStatus
from app.db.models.user import User
from app.db.repositories.document_repository import DocumentRepository
from app.services.exceptions import (
    DocumentNotFoundError,
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.storage import detect_file_type, get_storage, max_file_size_bytes
from app.storage.local import Storage


class DocumentService:
    """Orchestrates document uploads, listings, fetches, and deletes."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: Storage | None = None,
    ) -> None:
        self.session = session
        self.repo = DocumentRepository(session)
        # Late-bound via the factory so tests can swap the backend.
        self.storage = storage or get_storage()
        self.logger = get_logger(__name__)

    # ---------- Upload ----------

    async def create_document(
        self,
        *,
        owner: User,
        content: bytes,
        original_filename: str,
        content_type: str | None,
    ) -> Document:
        """Validate an upload, persist the bytes, return a new ORM instance.

        Raises:
            EmptyFileError: zero bytes.
            FileTooLargeError: size > configured maximum.
            UnsupportedFileTypeError: extension / MIME / magic bytes disagree.
        """
        size = len(content)
        if size == 0:
            raise EmptyFileError("Upload contains no data")

        cap = max_file_size_bytes()
        if size > cap:
            raise FileTooLargeError(actual_size=size, max_size=cap)

        file_type = detect_file_type(
            content=content,
            filename=original_filename,
            content_type=content_type,
        )
        if file_type is None:
            raise UnsupportedFileTypeError(
                "Unsupported file type",
                reason="detection",
            )

        # ``<uuid4().hex>.<file_type>`` — same spirit as the spec example
        # (random hex stem with the original extension preserved).
        stored_name = f"{uuid4().hex}.{file_type}"
        storage_path = await self.storage.save(
            content=content,
            stored_name=stored_name,
            file_type=file_type,
        )

        doc = Document(
            owner_id=owner.id,
            filename=stored_name,
            original_filename=original_filename,
            file_type=file_type,
            file_size=size,
            storage_path=storage_path,
            upload_status=DocumentUploadStatus.UPLOADING,
        )
        doc = await self.repo.create(doc)

        self.logger.info(
            "document.uploaded id=%s owner=%s size=%s type=%s",
            doc.id,
            owner.id,
            size,
            file_type,
        )
        return doc

    # ---------- Listing ----------

    async def list_user_documents(
        self,
        *,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        """Return the caller's documents, newest first."""
        return await self.repo.list_for_owner(owner_id, skip=skip, limit=limit)

    # ---------- Fetch (ownership-enforced) ----------

    async def get_document_for_owner(
        self,
        *,
        document_id: UUID,
        owner_id: UUID,
    ) -> Document:
        """Look up a document and verify ownership.

        Raises:
            DocumentNotFoundError: missing id, *or* owned by someone
                else. Callers must respond with 404 either way.
        """
        doc = await self.repo.get_by_id(document_id)
        if doc is None or doc.owner_id != owner_id:
            raise DocumentNotFoundError(document_id)
        return doc

    # ---------- Delete (file then row) ----------

    async def delete_document(
        self,
        *,
        document_id: UUID,
        owner_id: UUID,
    ) -> None:
        """Remove the file from storage, then the row from the database.

        File first, DB second: after this method returns successfully,
        the row will be gone on the next commit. Storage is permissive
        — if the file is already missing (a previous delete attempt
        partially completed), we log a warning but still delete the row.
        """
        doc = await self.get_document_for_owner(
            document_id=document_id,
            owner_id=owner_id,
        )

        await self.storage.delete(doc.storage_path)
        # Attempt to delete processing sidecar if it exists
        try:
            sidecar_path = f"{doc.storage_path}.processing.json"
            if await self.storage.exists(sidecar_path):
                await self.storage.delete(sidecar_path)
        except Exception as exc:
            self.logger.warning("Failed to delete sidecar for %s: %s", doc.id, exc)

        await self.repo.delete(doc)
        self.logger.info(
            "document.deleted id=%s owner=%s path=%s",
            doc.id,
            owner_id,
            doc.storage_path,
        )

    # ---------- Document Processing ----------

    async def process_document(self, document_id: UUID) -> None:
        """Run the document processing pipeline on the target document.

        Updates the database status to PROCESSING, runs extraction, cleaning, and
        chunking, saves the result as a sidecar JSON file, and sets the status to
        READY (or FAILED on error).
        """
        doc = await self.repo.get_by_id(document_id)
        if not doc:
            self.logger.error("Processing failed: document %s not found in DB", document_id)
            return

        # 1. Update status to PROCESSING
        await self.repo.set_status(doc, DocumentUploadStatus.PROCESSING)
        await self.session.commit()

        try:
            from pathlib import Path
            import json
            from app.core.config import settings
            from app.processing.pipeline import DocumentProcessingPipeline

            # Resolve absolute path to the uploaded file, respecting isolated storage in tests
            if hasattr(self.storage, "base_dir"):
                file_path = self.storage.base_dir / doc.storage_path
            else:
                file_path = Path(settings.UPLOAD_DIR) / doc.storage_path

            # 2. Run pipeline
            pipeline = DocumentProcessingPipeline()
            result = await pipeline.run(
                file_path=file_path,
                file_type=doc.file_type,
                filename=doc.original_filename,
                file_size=doc.file_size,
            )

            # 3. Save sidecar JSON next to the original file
            result_json = result.model_dump_json(indent=2)
            sidecar_name = f"{doc.filename}.processing.json"
            await self.storage.save(
                content=result_json.encode("utf-8"),
                stored_name=sidecar_name,
                file_type=doc.file_type,
            )

            # 4. Mark READY
            await self.repo.set_status(doc, DocumentUploadStatus.READY)
            await self.session.commit()
            self.logger.info("document.processed.success id=%s", document_id)

        except Exception as exc:
            self.logger.error("document.processed.failed id=%s error=%s", document_id, exc, exc_info=True)
            # Mark FAILED
            await self.repo.set_status(doc, DocumentUploadStatus.FAILED)
            await self.session.commit()

