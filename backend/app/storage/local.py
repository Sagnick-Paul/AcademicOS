"""Local-filesystem storage backend.

Writes go under ``<base_dir>/<file_type>/<stored_name>``. Atomic at
the filesystem level (write temp, ``os.replace`` onto target) so a
crash mid-upload can never leave a half-written file visible to
reads. The implementation is intentionally small — the goal is a
pluggable seam the future S3/MinIO backend will replace.
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.storage.types import FOLDER_BY_FILE_TYPE

logger = logging.getLogger(__name__)


class Storage(Protocol):
    """Pluggable storage seam.

    Every method is ``async`` so a future S3 backend can use
    ``aioboto3`` without changing call sites. ``save`` returns the
    opaque storage path the caller persists on the Document row;
    ``delete`` is permissive about missing files.
    """

    async def save(
        self,
        *,
        content: bytes,
        stored_name: str,
        file_type: str,
    ) -> str: ...

    async def delete(self, storage_path: str) -> None: ...

    async def exists(self, storage_path: str) -> bool: ...


class LocalStorage:
    """Filesystem-backed :class:`Storage` rooted at ``base_dir``."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir).resolve()

    # The path persisted in ``documents.storage_path``. Relative to
    # ``base_dir`` so the database stays portable across machines.
    @staticmethod
    def _relative(file_type: str, stored_name: str) -> str:
        folder = FOLDER_BY_FILE_TYPE.get(file_type)
        if folder is None:
            raise ValueError(f"Unsupported file_type for storage: {file_type!r}")
        return f"{folder}/{stored_name}"

    def _absolute(self, storage_path: str) -> Path:
        # Defend against traversal: reject anything that tries to
        # escape the base_dir by containing '..' or an absolute prefix.
        if os.path.isabs(storage_path) or ".." in Path(storage_path).parts:
            raise ValueError(f"Refusing unsafe storage path: {storage_path!r}")
        return self.base_dir / storage_path

    async def save(
        self,
        *,
        content: bytes,
        stored_name: str,
        file_type: str,
    ) -> str:
        rel = self._relative(file_type, stored_name)
        target = self._absolute(rel)
        target.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to a sibling tempfile, then rename.
        fd, tmp_path = tempfile.mkstemp(
            prefix=f".{stored_name}.",
            dir=target.parent,
        )
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            os.replace(tmp_path, target)
        except Exception:
            # Clean up the orphan temp file on any failure.
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise

        return rel

    async def delete(self, storage_path: str) -> None:
        target = self._absolute(storage_path)
        try:
            target.unlink()
        except FileNotFoundError:
            # DB row is authoritative; treat missing files as a soft
            # warning rather than a 5xx-causing error.
            logger.warning("storage.delete: file not found at %s", target)

    async def exists(self, storage_path: str) -> bool:
        return self._absolute(storage_path).is_file()


# ---------- Singleton factory ----------

_storage_singleton: Storage | None = None


def get_storage(base_dir: str | None = None) -> Storage:
    """Return the process-wide :class:`Storage` instance.

    Pass ``base_dir`` explicitly only from tests; production code
    should hit the default ``settings.UPLOAD_DIR``.
    """
    global _storage_singleton
    if _storage_singleton is None:
        resolved = Path(base_dir) if base_dir is not None else Path(settings.UPLOAD_DIR)
        _storage_singleton = LocalStorage(resolved)
    return _storage_singleton


def reset_storage_singleton() -> None:
    """Drop the singleton so the next :func:`get_storage` re-initializes.

    Test-only helper. Production code never calls this.
    """
    global _storage_singleton
    _storage_singleton = None


__all__ = ["Storage", "LocalStorage", "get_storage", "reset_storage_singleton"]
