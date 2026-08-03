"""Enumerations shared across ORM models.

Stored as `str` in the database for forward compatibility (new values
won't break existing rows). Implemented with `str, Enum` so the code
runs on Python 3.10+.
"""
from __future__ import annotations

from enum import Enum


class _StrEnum(str, Enum):
    """Base for string-valued enums that compare equal to their value."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


class DocumentUploadStatus(_StrEnum):
    """Lifecycle of an uploaded document."""

    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ChatRole(_StrEnum):
    """Speaker role in a chat message."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
