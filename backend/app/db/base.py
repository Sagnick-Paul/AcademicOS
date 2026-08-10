"""SQLAlchemy declarative base and shared mixins.

All ORM models inherit from `Base`. Common columns (UUID primary key,
timestamps) live in mixins to keep model definitions clean.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.types import GUID


def _utcnow() -> datetime:
    """Return a timezone-aware UTC ``datetime``.

    Used as the Python-side default for ``created_at`` so that rows
    inserted in the same transaction — where SQLite's ``func.now()``
    resolves to a single shared timestamp — still get monotonically
    increasing, microsecond-precision values captured at Python
    instance construction time. This guarantees deterministic ordering
    of chat history rows even under tight-loop test fixtures.
    """
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class UUIDPKMixin:
    """Adds a UUID primary-key column named `id`.

    Python-side default uses :func:`uuid.uuid4` so unsaved instances get
    a stable identifier; the database can also generate one.
    """

    id: Mapped[Any] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    """Adds timezone-aware `created_at` and `updated_at` columns.

    ``created_at`` carries BOTH a Python-side default and a server-side
    default. The Python default fires at instance construction so
    monotonic ordering survives tight insert loops where the database
    would otherwise stamp every row with the same ``now()``.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__: list[str] = ["Base", "UUIDPKMixin", "TimestampMixin", "Any"]
