"""Document service.

Owns:

* validating uploads (size, content, type)
* coordinating the storage layer and the ORM model
* enforcing per-user ownership on every read / delete
* enforcing course ownership on every course assignment (Phase 6B)
* validating and applying the Phase 6C classification + metadata
  fields, with correct omit-vs-null PATCH semantics

The endpoint layer is thin — it calls the service, translates domain
exceptions into HTTP responses, and commits the session. No business
logic lives outside this module (and the storage package beneath it).
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID, uuid4

# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.document import Document
from app.db.models.enums import DocumentType, DocumentUploadStatus
from app.db.models.user import User
from app.db.repositories.course_repository import CourseRepository
from app.db.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentUpdate
from app.services.exceptions import (
    CourseNotFoundError,
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
        course_repo: CourseRepository | None = None,
    ) -> None:
        self.session = session
        self.repo = DocumentRepository(session)
        # Late-bound via the factory so tests can swap the backend.
        self.storage = storage or get_storage()
        self.course_repo = course_repo or CourseRepository(session)
        self.logger = get_logger(__name__)

    # ---------- Course ownership ----------

    async def _assert_course_owned_by(
        self,
        course_id: UUID,
        owner_id: UUID,
    ) -> None:
        """Verify ``course_id`` exists AND belongs to ``owner_id``.

        Both "no such course" and "owned by another user" raise the
        same :class:`CourseNotFoundError` so the endpoint can answer
        404 without leaking which case fired.
        """
        course = await self.course_repo.get_for_owner(
            course_id, owner_id=owner_id
        )
        if course is None:
            raise CourseNotFoundError(course_id)

    # ---------- Upload ----------

    async def create_document(
        self,
        *,
        owner: User,
        content: bytes,
        original_filename: str,
        content_type: str | None,
        document_type: DocumentType | None = None,
        document_metadata: dict | None = None,
    ) -> Document:
        """Validate an upload, persist the bytes, return a new ORM instance.

        Phase 6C adds optional ``document_type`` and ``document_metadata``
        arguments. When ``document_type`` is omitted the row is stamped
        with ``DocumentType.OTHER`` — the deliberate default — so new
        uploads are never uncategorised. ``document_metadata`` is
        stored as-is (already validated by the Pydantic schema at the
        edge).

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
            document_type=document_type or DocumentType.OTHER,
            document_metadata=document_metadata,
        )
        doc = await self.repo.create(doc)

        self.logger.info(
            "document.uploaded id=%s owner=%s size=%s type=%s doc_type=%s",
            doc.id,
            owner.id,
            size,
            file_type,
            doc.document_type,
        )
        return doc

    # ---------- Listing ----------

    async def list_user_documents(
        self,
        *,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100,
        course_id: UUID | None = None,
        document_type: DocumentType | None = None,
    ) -> Sequence[Document]:
        """Return the caller's documents, newest first.

        When ``course_id`` is supplied, restrict to that course. The
        service first verifies the course is owned by the caller, then
        delegates the actual filter to the repository. The Phase 6C
        ``document_type`` filter composes with ``course_id``.
        """
        if course_id is not None:
            await self._assert_course_owned_by(course_id, owner_id)
        return await self.repo.list_for_owner(
            owner_id,
            skip=skip,
            limit=limit,
            course_id=course_id,
            document_type=document_type,
        )

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

    # ---------- Update (course link) ----------

    async def update_document_course(
        self,
        *,
        document_id: UUID,
        owner_id: UUID,
        course_id: UUID | None,
    ) -> Document:
        """Assign, change, or clear a document's course link.

        Raises:
            DocumentNotFoundError: missing or not-owned document.
            CourseNotFoundError: ``course_id`` was provided but does
                not belong to ``owner_id`` (or does not exist).
        """
        doc = await self.get_document_for_owner(
            document_id=document_id, owner_id=owner_id,
        )
        if course_id is not None:
            await self._assert_course_owned_by(course_id, owner_id)

        doc = await self.repo.set_course(doc, course_id)
        self.logger.info(
            "document.course_set id=%s owner=%s course=%s",
            doc.id, owner_id, course_id,
        )
        return doc

    # ---------- Update (Phase 6C classification + metadata) ----------

    async def update_document(
        self,
        *,
        document_id: UUID,
        owner_id: UUID,
        payload: DocumentUpdate,
    ) -> Document:
        """Apply a Phase 6C-aware partial update.

        Single funnel for PATCH /documents/{id}. It resolves the
        omit-vs-null-vs-value distinction on every Phase 6C field
        (mirroring the Phase 6B course_id pattern) and writes only
        what actually changed.

        Distinctions:
        * Field omitted (``not in model_fields_set``) → leave alone.
        * Field explicitly ``null`` → write NULL.
        * Field provided → write through.
        """
        doc = await self.get_document_for_owner(
            document_id=document_id, owner_id=owner_id,
        )

        fields_set = payload.model_fields_set
        updates: dict = {}

        # ``document_type``
        if "document_type" in fields_set:
            updates["document_type"] = payload.document_type

        # ``document_metadata``: Pydantic nested model → dict, or None.
        if "document_metadata" in fields_set:
            if payload.document_metadata is None:
                updates["document_metadata"] = None
            else:
                updates["document_metadata"] = (
                    payload.document_metadata.model_dump(exclude_none=True)
                )

        # ``course_id``
        if "course_id" in fields_set:
            if payload.course_id is not None:
                await self._assert_course_owned_by(payload.course_id, owner_id)
            updates["course_id"] = payload.course_id

        if not updates:
            return doc

        doc = await self.repo.update(doc, updates)
        self.logger.info(
            "document.classification_set id=%s owner=%s fields=%s",
            doc.id,
            owner_id,
            sorted(updates.keys()),
        )
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

            # 2. Run pipeline with dependency injection
            from app.processing.embeddings.provider import SentenceTransformerEmbeddingProvider
            from app.processing.embeddings.qdrant import QdrantVectorStore

            provider = SentenceTransformerEmbeddingProvider()
            vector_store = QdrantVectorStore()

            pipeline = DocumentProcessingPipeline(
                embedding_provider=provider,
                vector_store=vector_store,
            )
            result = await pipeline.run(
                file_path=file_path,
                file_type=doc.file_type,
                filename=doc.original_filename,
                file_size=doc.file_size,
                document_id=doc.id,
                owner_id=doc.owner_id,
                course_id=doc.course_id,
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

