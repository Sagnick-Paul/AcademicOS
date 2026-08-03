"""Shared FastAPI dependencies.

Common `Depends(...)` callables: DB session, current user, settings, and
other cross-cutting injections. Implementations land here as features
are added.
"""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db


__all__ = ["get_db", "get_settings", "get_settings_dep"]


def get_settings_dep() -> Settings:
    """Settings dependency wrapper for `Depends(...)`."""
    return get_settings()


# Type aliases for clean signatures in endpoints.
DBSession = AsyncSession
SettingsDep = Depends(get_settings_dep)


async def _db_session_dep() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


DBDep = Depends(_db_session_dep)
