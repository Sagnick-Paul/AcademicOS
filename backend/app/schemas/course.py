"""Pydantic schemas for :class:`app.db.models.course.Course`.

Owner is always derived from the authenticated user — clients cannot
supply `owner_id`. Whitespace is trimmed and the (owner, name)
uniqueness constraint is enforced at the database level.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Course name is required. Cap at 255 to match the underlying column
# and keep totals predictable; trim surrounding whitespace so callers
# can be sloppy without producing duplicate rows.
CourseNameStr = Annotated[str, Field(min_length=1, max_length=255)]
# Course code is optional. Allow a reasonable size envelope (a typical
# university code is well under 32 chars; 64 gives room for the
# longest real-world values).
CourseCodeStr = Annotated[str, Field(min_length=1, max_length=64)]
# Description is optional. Cap at 2000 chars — long enough for a
# paragraph, short enough to keep the table sane.
CourseDescriptionStr = Annotated[str, Field(min_length=1, max_length=2000)]


def _normalize_name(value: str) -> str:
    """Trim a name; empty-after-trim is rejected by ``min_length=1``."""
    return value.strip()


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    """Trim optional text fields. ``None`` passes through unchanged.

    An empty string after trim is treated as "not provided" (normalized
    to ``None``) so callers cannot sneak whitespace-only values past
    the required-field guards downstream.
    """
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class CourseBase(BaseModel):
    """Shared fields for course payloads."""

    model_config = ConfigDict(extra="forbid")

    name: CourseNameStr
    code: Optional[CourseCodeStr] = None
    description: Optional[CourseDescriptionStr] = None

    @field_validator("name", mode="before")
    @classmethod
    def _trim_name(cls, v: object) -> object:
        if isinstance(v, str):
            trimmed = _normalize_name(v)
            if not trimmed:
                raise ValueError("Course name must not be empty or only whitespace")
            return trimmed
        return v

    @field_validator("code", "description", mode="before")
    @classmethod
    def _trim_optional(cls, v: object) -> object:
        return _normalize_optional_text(v)  # type: ignore[arg-type]


class CourseCreate(CourseBase):
    """Payload for creating a course.

    ``owner_id`` is set by the service layer from the authenticated
    user, not by the client, so it is intentionally absent here.
    """


class CourseUpdate(BaseModel):
    """Partial update — every field is optional.

    ``extra="forbid"`` rejects unknown fields (including the forbidden
    ``owner_id``) so the wire contract is explicit.
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[CourseNameStr] = None
    code: Optional[CourseCodeStr] = None
    description: Optional[CourseDescriptionStr] = None

    @field_validator("name", mode="before")
    @classmethod
    def _trim_name(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            trimmed = _normalize_name(v)
            if not trimmed:
                raise ValueError("Course name must not be empty or only whitespace")
            return trimmed
        return v

    @field_validator("code", "description", mode="before")
    @classmethod
    def _trim_optional(cls, v: object) -> object:
        if v is None:
            return None
        return _normalize_optional_text(v)  # type: ignore[arg-type]


class CourseResponse(BaseModel):
    """Public course representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CourseListResponse(BaseModel):
    """Envelope for the list endpoint.

    A wrapper rather than a bare ``list[...]`` keeps the wire contract
    stable if pagination metadata is added later.
    """

    items: list[CourseResponse]


__all__: list[str] = [
    "CourseBase",
    "CourseCreate",
    "CourseUpdate",
    "CourseResponse",
    "CourseListResponse",
]
