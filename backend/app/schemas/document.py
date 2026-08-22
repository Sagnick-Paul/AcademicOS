"""Pydantic schemas for :class:`app.db.models.document.Document`.

The service layer translates between these DTOs and ORM rows.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Optional, Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models.enums import DocumentType, DocumentUploadStatus


# Filenames on most filesystems top out at 255 bytes; cap safely.
FileNameStr = Annotated[str, Field(min_length=1, max_length=512)]
PathStr = Annotated[str, Field(min_length=1, max_length=1024)]
TypeStr = Annotated[str, Field(min_length=1, max_length=64)]

# Metadata caps. Author / subject / code-like strings are short.
_META_AUTHOR_MAX = 255
_META_SUBJECT_MAX = 255
_META_SEMESTER_MAX = 64
_META_ACADEMIC_YEAR_MAX = 64
_META_TAG_MAX = 64
_META_TAGS_MAX_COUNT = 32


def _normalize_optional_text(value: object) -> Optional[str]:
    """Trim a string. ``None`` and empty-after-trim both → ``None``.

    Non-strings pass through untouched so Pydantic still surfaces its
    own type error.
    """
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value  # type: ignore[return-value]


# ---------- Document metadata (Phase 6C) ----------


class DocumentMetadata(BaseModel):
    """Structured academic metadata attached to a Document.

    Optional, partial. Intentionally small: each field captures a
    facet of academic provenance that we expect to filter or group
    documents by later, NOT a copy of fields that already live on
    the document row (file_type, course, upload status, etc.).

    Constraints:

    * ``extra="forbid"`` — unknown fields are rejected so payloads
      cannot grow into a junk drawer.
    * Lists are deduplicated and whitespace-trimmed.
    """

    model_config = ConfigDict(extra="forbid")

    author: Optional[Annotated[str, Field(max_length=_META_AUTHOR_MAX)]] = None
    subject: Optional[Annotated[str, Field(max_length=_META_SUBJECT_MAX)]] = None
    semester: Optional[Annotated[str, Field(max_length=_META_SEMESTER_MAX)]] = None
    academic_year: Optional[
        Annotated[str, Field(max_length=_META_ACADEMIC_YEAR_MAX)]
    ] = None
    tags: Optional[
        Annotated[list[Annotated[str, Field(max_length=_META_TAG_MAX)]],
                  Field(max_length=_META_TAGS_MAX_COUNT)]
    ] = None

    @field_validator("author", "subject", mode="before")
    @classmethod
    def _trim_short_text(cls, v: object) -> object:
        return _normalize_optional_text(v)

    @field_validator("semester", "academic_year", mode="before")
    @classmethod
    def _trim_code(cls, v: object) -> object:
        return _normalize_optional_text(v)

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, v: object) -> object:
        if v is None:
            return None
        if not isinstance(v, list):
            return v  # let Pydantic raise its own type error
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in v:
            if not isinstance(item, str):
                return v  # let Pydantic raise its own type error
            stripped = item.strip()
            if not stripped:
                # Empty tag string is silently dropped: the alternative
                # is to reject the whole list, which punishes a single
                # accidental whitespace.
                continue
            key = stripped.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(stripped)
            if len(cleaned) > _META_TAGS_MAX_COUNT:
                # Truncate quietly rather than rejecting: a 33rd tag
                # rarely matters and rejecting would force clients
                # to reconstruct their list before every save.
                break
        return cleaned or None


# ---------- Document type (Phase 6C) ----------


def _coerce_document_type(value: object) -> Optional[DocumentType]:
    """Best-effort coercion used by response schemas (read path only).

    Accepts:

    * a :class:`DocumentType` enum value
    * the raw string ``"lecture_notes"`` and friends
    * ``None`` (preserved; signals "uncategorised" in legacy rows)

    Anything else is rejected so a typo cannot leak into the API
    output.
    """
    if value is None:
        return None
    if isinstance(value, DocumentType):
        return value
    if isinstance(value, str):
        try:
            return DocumentType(value)
        except ValueError as exc:
            raise ValueError(
                f"Unknown document type: {value!r}"
            ) from exc
    raise ValueError(f"Unsupported document type: {value!r}")


# ---------- Schemas ----------


class DocumentMetadataPayload(BaseModel):
    """Wire shape for the inline ``metadata`` field on create/update.

    Lives outside :class:`DocumentMetadata` because Pydantic v1 ``dict``
    encoding vs. embedded-model encoding differ; tests and clients are
    easier to debug when the wire schema is a standalone model. The
    constraints are the same.
    """

    model_config = ConfigDict(extra="forbid")

    author: Optional[Annotated[str, Field(max_length=_META_AUTHOR_MAX)]] = None
    subject: Optional[Annotated[str, Field(max_length=_META_SUBJECT_MAX)]] = None
    semester: Optional[Annotated[str, Field(max_length=_META_SEMESTER_MAX)]] = None
    academic_year: Optional[
        Annotated[str, Field(max_length=_META_ACADEMIC_YEAR_MAX)]
    ] = None
    tags: Optional[
        Annotated[list[Annotated[str, Field(max_length=_META_TAG_MAX)]],
                  Field(max_length=_META_TAGS_MAX_COUNT)]
    ] = None

    @field_validator("author", "subject", mode="before")
    @classmethod
    def _trim_short_text(cls, v: object) -> object:
        return _normalize_optional_text(v)

    @field_validator("semester", "academic_year", mode="before")
    @classmethod
    def _trim_code(cls, v: object) -> object:
        return _normalize_optional_text(v)

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, v: object) -> object:
        if v is None:
            return None
        if not isinstance(v, list):
            return v
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in v:
            if not isinstance(item, str):
                return v
            stripped = item.strip()
            if not stripped:
                continue
            key = stripped.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(stripped)
            if len(cleaned) > _META_TAGS_MAX_COUNT:
                break
        return cleaned or None


class DocumentBase(BaseModel):
    """Shared document fields."""

    filename: FileNameStr
    original_filename: FileNameStr
    file_type: TypeStr
    file_size: Annotated[int, Field(ge=0)]
    storage_path: PathStr
    upload_status: DocumentUploadStatus = DocumentUploadStatus.PENDING

    # Phase 6C — academic classification and structured metadata.
    document_type: Optional[DocumentType] = None
    document_metadata: Optional[DocumentMetadataPayload] = None


class DocumentCreate(DocumentBase):
    """Payload for creating a document record.

    `owner_id` is set by the service layer from the authenticated user,
    not by the client, so it is omitted here.
    """


class DocumentUpdate(BaseModel):
    """Partial update — typically the upload status / metadata fixups.

    Phase 6B adds ``course_id``: a non-null value assigns the document
    to one of the caller's courses; ``null`` removes any existing
    course link. The service layer validates ownership before writing.

    Phase 6C adds ``document_type`` and ``document_metadata``. As with
    ``course_id``:

    * omitted field → leave current value alone
    * ``null`` → clear (type → NULL, metadata → NULL)
    * value → write through (type → enum value, metadata → dict)
    """

    model_config = ConfigDict(extra="forbid")

    filename: FileNameStr | None = None
    file_type: TypeStr | None = None
    upload_status: DocumentUploadStatus | None = None
    course_id: Optional[UUID] = None

    # Phase 6C — the new mutable fields. ``DocumentType | None`` because
    # ``None`` here means "client explicitly cleared it".
    document_type: Optional[DocumentType] = None
    document_metadata: Optional[DocumentMetadataPayload] = None


class DocumentResponse(DocumentBase):
    """Public document representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    # Phase 6B: nullable course link. ``null`` means "uncoursed".
    course_id: Optional[UUID] = None
    # Phase 6C: document_metadata may be missing on legacy rows.
    document_metadata: Optional[DocumentMetadataPayload] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("document_type", mode="before")
    @classmethod
    def _coerce_type(cls, v: object) -> object:
        return _coerce_document_type(v)


__all__ = [
    "DocumentMetadata",
    "DocumentMetadataPayload",
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
]


# Silence linters — keep ``Any`` / ``Sequence`` / ``BaseModel`` exports
# available for future extensions without an import-side rewrite.
__all__ += ["BaseModel", "Any", "Sequence"]
