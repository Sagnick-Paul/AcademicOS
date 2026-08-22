"""File-type allow-list and content sniffing for uploads.

Kept as a pure-data module so the service layer and any future
background workers can import the constants without dragging in
filesystem dependencies.

``detect_file_type`` is the single source of truth: a file is
considered supported only when its filename extension, declared
Content-Type, and a small magic-byte prefix all agree on a single
canonical type. Any mismatch returns ``None`` and the upload is
rejected.
"""
from __future__ import annotations

from typing import Final

from app.core.config import settings


# Canonical short names stored in ``documents.file_type``.
SUPPORTED_FILE_TYPES: Final[frozenset[str]] = frozenset(
    {"pdf", "ppt", "pptx", "png", "jpg", "jpeg", "txt"}
)


# Mapping canonical name → permitted filename extensions (lowercase, no dot).
ALLOWED_EXTENSIONS: Final[dict[str, tuple[str, ...]]] = {
    "pdf": ("pdf",),
    "pptx": ("pptx", "ppt"),  # ``.ppt`` and ``.pptx`` both naming the same Office family
    "png": ("png",),
    "jpg": ("jpg", "jpeg"),
    "jpeg": ("jpg", "jpeg"),
    "txt": ("txt",),
}


# Mapping canonical name → permitted Content-Type values.
ALLOWED_MIME_TYPES: Final[dict[str, tuple[str, ...]]] = {
    "pdf": ("application/pdf",),
    "pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
        # permissive aliases seen in the wild from various browsers
        "application/octet-stream",
    ),
    "png": ("image/png",),
    "jpg": ("image/jpeg", "image/jpg"),
    "jpeg": ("image/jpeg", "image/jpg"),
    "txt": ("text/plain",),
}


# Per-type folder name used both in the storage backend and when
# deciding which subdirectory under UPLOAD_DIR to write to. Kept
# lowercase and stable — changing it is a stored-file migration.
FOLDER_BY_FILE_TYPE: Final[dict[str, str]] = {
    "pdf": "pdf",
    "ppt": "ppt",
    "pptx": "ppt",
    "png": "images",
    "jpg": "images",
    "jpeg": "images",
    "txt": "text",
}


# ---------- Magic-byte signatures ----------
# See https://www.garykessler.net/library/file_sigs.html for the
# authoritative table. Snippets are short on purpose — anything that
# doesn't match here is rejected before we waste a write on it.

_PDF_PREFIX = b"%PDF-"
_JPEG_PREFIX = b"\xff\xd8\xff"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_ZIP_LOCAL_HEADER = b"PK\x03\x04"
_OLE_COMPOUND_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def max_file_size_bytes() -> int:
    """Maximum upload size in bytes, computed from settings at call time."""
    return settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _extension(filename: str) -> str:
    """Return the lowercase extension without the leading dot. Empty on no extension."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def _content_type_matches(canonical: str, declared: str | None) -> bool:
    if not declared:
        return False
    declared_norm = declared.split(";", 1)[0].strip().lower()
    if declared_norm == "application/octet-stream":
        # Some browsers report OOXML as octet-stream — fall back to
        # accepting it for the pptx family, which we'd otherwise reject.
        return canonical == "pptx"
    return declared_norm in {m.lower() for m in ALLOWED_MIME_TYPES[canonical]}


def _candidate_from_magic(content: bytes) -> tuple[str, ...] | None:
    """Return canonical type names whose magic bytes match ``content``.

    Returns at most one entry for PDF / JPEG / PNG (their bytes are
    unambiguous). For Office types, returns both "pptx" and "ppt" — the
    filename and Content-Type have to disambiguate.
    """
    if content.startswith(_PDF_PREFIX):
        return ("pdf",)
    if content.startswith(_JPEG_PREFIX):
        return ("jpg", "jpeg")  # JPEG has no separate "jpeg" magic; alias both
    if content.startswith(_PNG_SIGNATURE):
        return ("png",)
    if content.startswith(_OLE_COMPOUND_MAGIC) or content.startswith(_ZIP_LOCAL_HEADER):
        # PPT (OLE compound binary) or PPTX (ZIP container) — both possible.
        return ("pptx", "ppt")
    return None


def detect_file_type(
    content: bytes,
    filename: str,
    content_type: str | None,
) -> str | None:
    """Resolve a canonical file type, or ``None`` if the file is unsupported.

    All three signals must agree on a single canonical name:

    1. Filename extension must be in :data:`ALLOWED_EXTENSIONS`.
    2. Content-Type header must be in :data:`ALLOWED_MIME_TYPES`.
    3. Magic bytes must match a recognised signature.

    Returns the canonical name (``"pdf"``, ``"ppt"``, etc.) on success.
    """
    ext = _extension(filename)
    candidates_by_ext = [name for name, exts in ALLOWED_EXTENSIONS.items() if ext in exts]
    if len(candidates_by_ext) != 1:
        return None
    by_ext = candidates_by_ext[0]

    if not _content_type_matches(by_ext, content_type):
        return None

    magic_candidates = _candidate_from_magic(content)
    if magic_candidates is None or by_ext not in magic_candidates:
        return None

    return by_ext


__all__ = [
    "SUPPORTED_FILE_TYPES",
    "ALLOWED_EXTENSIONS",
    "ALLOWED_MIME_TYPES",
    "FOLDER_BY_FILE_TYPE",
    "max_file_size_bytes",
    "detect_file_type",
]
