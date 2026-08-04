"""Object storage abstractions.

Local filesystem for development, S3/MinIO/GCS in production. One
client interface, swappable backends.
"""
from __future__ import annotations

from app.storage.local import LocalStorage, get_storage, reset_storage_singleton
from app.storage.types import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    FOLDER_BY_FILE_TYPE,
    SUPPORTED_FILE_TYPES,
    detect_file_type,
    max_file_size_bytes,
)

__all__ = [
    "LocalStorage",
    "get_storage",
    "reset_storage_singleton",
    "ALLOWED_EXTENSIONS",
    "ALLOWED_MIME_TYPES",
    "FOLDER_BY_FILE_TYPE",
    "SUPPORTED_FILE_TYPES",
    "detect_file_type",
    "max_file_size_bytes",
]
