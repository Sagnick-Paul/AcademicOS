"""Document endpoints.

Five thin handlers: upload, list, get, update, delete. Business logic
lives in :class:`app.services.document_service.DocumentService`;
this module only translates domain exceptions into HTTP responses and
commits the session after writes that must be visible to subsequent
requests.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
# pyrefly: ignore [missing-import]
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

# pyrefly: ignore [missing-import]
from app.api.deps import get_current_active_user, get_document_service
from app.db.models.enums import DocumentType
from app.db.models.user import User
from app.schemas.document import (
    DocumentMetadataPayload,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.document_service import DocumentService
from app.services.exceptions import (
    CourseNotFoundError,
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


# Accept a JSON-encoded metadata blob on upload. The OpenAPI surface
# stays text-only because multipart structs are awkward to express;
# clients can ``document_metadata=<urlencoded-json>``.
def _parse_upload_metadata(raw: Optional[str]):
    """Parse an optional JSON metadata payload from the upload form.

    ``None`` and empty strings are accepted and mapped to ``None``;
    malformed JSON or invalid schema is rejected with 422.
    """
    if raw is None:
        return None
    if raw.strip() == "":
        return None
    try:
        return DocumentMetadataPayload.model_validate_json(raw)
    except ValidationError as exc:
        raise RequestValidationError(errors=exc.errors())


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
    document_type: Optional[DocumentType] = Form(default=None),
    document_metadata: Optional[str] = Form(default=None),
) -> DocumentResponse:
    """Accept a multipart file upload and persist it for the authenticated user.

    Validates extension, Content-Type header, magic bytes, and size.
    Phase 6C optionally accepts ``document_type`` (a stringified enum
    member like ``lecture_notes``) and ``document_metadata`` (a
    JSON-encoded payload matching :class:`DocumentMetadataPayload`).
    Both default to ``None`` — uploads that omit them get
    ``document_type=OTHER`` and no metadata.

    Returns the persisted document metadata on success.

    Raises:
        400: zero-byte file.
        413: file exceeds the configured maximum.
        415: unsupported or spoofed file type.
        422: malformed ``document_type`` or ``document_metadata``.
    """
    parsed_metadata = _parse_upload_metadata(document_metadata)

    content = await file.read()
    try:
        doc = await service.create_document(
            owner=current,
            content=content,
            original_filename=file.filename or "unnamed",
            content_type=file.content_type,
            document_type=document_type,
            document_metadata=(
                parsed_metadata.model_dump(exclude_none=True)
                if parsed_metadata is not None
                else None
            ),
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
    course_id: UUID | None = None,
    document_type: DocumentType | None = None,
) -> list[DocumentResponse]:
    """Return the authenticated user's documents, newest first.

    Phase 6B: ``?course_id=<uuid>`` filters to documents belonging to
    the named course. The course must be owned by the caller — a
    foreign or missing course id returns 404.

    Phase 6C: ``?document_type=<member>`` filters to documents with the
    requested academic classification. The two filters compose: when
    both are supplied the result is the intersection. Omitting both
    returns every document owned by the caller (legacy behaviour).
    """
    try:
        rows = await service.list_user_documents(
            owner_id=current.id,
            skip=skip,
            limit=limit,
            course_id=course_id,
            document_type=document_type,
        )
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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


@router.get(
    "/{document_id}/content",
    summary="Download a document's content",
)
async def get_my_document_content(
    document_id: UUID,
    current: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> Response:
    """Serve the actual file for a document owned by the authenticated user.

    Ownership is verified before serving the file.
    """
    try:
        doc = await service.get_document_for_owner(
            document_id=document_id, owner_id=current.id
        )
        path = await service.storage.get_absolute_path(doc.storage_path)
        return FileResponse(
            path=path,
            filename=doc.original_filename,
        )
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None



@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update a document",
)
async def update_my_document(
    document_id: UUID,
    payload: DocumentUpdate,
    current: User = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Update a document owned by the caller.

    Phase 6B: ``course_id`` — supply a UUID to attach the document to
    one of the caller's courses; ``null`` to clear the link; omit the
    key to leave it alone.

    Phase 6C: ``document_type`` and ``document_metadata`` follow the
    same omit-vs-null-vs-value semantics. The service resolves the
    distinction and writes only what actually changed. A foreign or
    missing course id (when supplied) returns 404.
    """
    fields_set = payload.model_fields_set

    try:
        # Two specialised routes keep the clean error surface:
        # 1. Only ``course_id`` supplied → reuse the Phase 6B path
        #    so existing 404 semantics stay identical.
        # 2. Any Phase 6C field touched (regardless of course_id) →
        #    route through ``update_document`` which handles both.
        only_course = (
            "course_id" in fields_set
            and "document_type" not in fields_set
            and "document_metadata" not in fields_set
        )
        if only_course:
            doc = await service.update_document_course(
                document_id=document_id,
                owner_id=current.id,
                course_id=payload.course_id,
            )
        else:
            doc = await service.update_document(
                document_id=document_id,
                owner_id=current.id,
                payload=payload,
            )
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _commit(service.session)
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
