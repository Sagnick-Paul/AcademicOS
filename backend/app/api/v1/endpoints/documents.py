"""Document endpoints.

Four thin handlers: upload, list, get, delete. Business logic lives in
:class:`app.services.document_service.DocumentService`; this module
only translates domain exceptions into HTTP responses and commits the
session after writes that must be visible to subsequent requests.
"""
from __future__ import annotations

from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, BackgroundTasks
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

# pyrefly: ignore [missing-import]
from app.api.deps import get_current_active_user, get_document_service
from app.db.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService
from app.services.exceptions import (
    DocumentNotFoundError,
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

router = APIRouter()


# ---------- helpers ----------


async def _commit(session: AsyncSession) -> None:
    """Commit the current session.

    Duplicated from ``auth.py`` deliberately so endpoints stay
    self-contained and there is no import cycle (auth already imports
    deps which imports services).
    """
    await session.commit()


# ---------- endpoints ----------


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Upload a document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Accept a multipart file upload and persist it for the authenticated user.

    Validates extension, Content-Type header, magic bytes, and size.
    Returns the persisted document metadata on success.

    Raises:
        400: zero-byte file.
        413: file exceeds the configured maximum.
        415: unsupported or spoofed file type.
    """
    content = await file.read()
    try:
        doc = await service.create_document(
            owner=current,
            content=content,
            original_filename=file.filename or "unnamed",
            content_type=file.content_type,
        )
    except EmptyFileError:
        raise HTTPException(status_code=400, detail="Empty upload") from None
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {exc.max_size} bytes",
        ) from None
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {exc.reason}",
        ) from None

    await _commit(service.session)

    # Queue the document processing pipeline to run in the background
    background_tasks.add_task(service.process_document, doc.id)

    return DocumentResponse.model_validate(doc)


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List current user's documents",
)
async def list_my_documents(
    current: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
    skip: int = 0,
    limit: int = 100,
) -> list[DocumentResponse]:
    """Return the authenticated user's documents, newest first."""
    rows = await service.list_user_documents(
        owner_id=current.id, skip=skip, limit=limit
    )
    return [DocumentResponse.model_validate(r) for r in rows]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a single document",
)
async def get_my_document(
    document_id: UUID,
    current: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Return metadata for a document owned by the authenticated user.

    Returns 404 for both missing IDs and IDs owned by another user so
    that the endpoint cannot be used to enumerate other users' content.
    """
    try:
        doc = await service.get_document_for_owner(
            document_id=document_id, owner_id=current.id
        )
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    status_code=204,
    summary="Delete a document",
)
async def delete_my_document(
    document_id: UUID,
    current: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> Response:
    """Delete a document (file + DB row) owned by the authenticated user.

    Returns 404 for missing or not-owned documents (same as GET).
    Returns 204 No Content on success.
    """
    try:
        await service.delete_document(document_id=document_id, owner_id=current.id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    await _commit(service.session)
    return Response(status_code=204)
