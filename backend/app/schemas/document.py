"""Pydantic schemas for :class:`app.db.models.document.Document`.

The service layer translates between these DTOs and ORM rows.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import DocumentUploadStatus


# Filenames on most filesystems top out at 255 bytes; cap safely.
FileNameStr = Annotated[str, Field(min_length=1, max_length=512)]
PathStr = Annotated[str, Field(min_length=1, max_length=1024)]
TypeStr = Annotated[str, Field(min_length=1, max_length=64)]


class DocumentBase(BaseModel):
    """Shared document fields."""

    filename: FileNameStr
    original_filename: FileNameStr
    file_type: TypeStr
    file_size: Annotated[int, Field(ge=0)]
    storage_path: PathStr
    upload_status: DocumentUploadStatus = DocumentUploadStatus.PENDING


class DocumentCreate(DocumentBase):
    """Payload for creating a document record.

    `owner_id` is set by the service layer from the authenticated user,
    not by the client, so it is omitted here.
    """


class DocumentUpdate(BaseModel):
    """Partial update — typically the upload status / metadata fixups."""

    model_config = ConfigDict(extra="forbid")

    filename: FileNameStr | None = None
    file_type: TypeStr | None = None
    upload_status: DocumentUploadStatus | None = None


class DocumentResponse(DocumentBase):
    """Public document representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
