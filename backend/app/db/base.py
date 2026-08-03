"""SQLAlchemy declarative base and shared mixins.

All ORM models inherit from `Base`. Common columns (UUID primary key,
timestamps) live in mixins to keep model definitions clean.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.types import GUID


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
    """Adds timezone-aware `created_at` and `updated_at` columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__: list[str] = ["Base", "UUIDPKMixin", "TimestampMixin", "Any"]
