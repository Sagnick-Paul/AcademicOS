"""Custom SQLAlchemy types.

`GUID` is a cross-database UUID column. We use the native `UUID` type on
PostgreSQL and fall back to `CHAR(36)` on other backends so models are
portable for tests.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CHAR, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class GUID(TypeDecorator):
    """Platform-independent UUID column.

    Stores as native UUID on PostgreSQL and as CHAR(32) (hex) elsewhere.
    Always accepts/returns :class:`uuid.UUID` instances.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any | None:
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        # On non-Postgres we store the canonical 36-char string form.
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
