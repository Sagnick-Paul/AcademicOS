"""User repository.

Adds user-specific lookups on top of the generic CRUD. Authentication
itself lives in `app.core.security`; this module is data access only.
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Async repository for :class:`app.db.models.user.User`."""

    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ---------- Lookups ----------

    async def get_by_email(self, email: str) -> User | None:
        """Find a user by their (unique) email address."""
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
        self, user_id: UUID | str, *, raise_if_missing: bool = False
    ) -> User | None:
        """Look up a user by primary key."""
        return await super().get_by_id(user_id, raise_if_missing=raise_if_missing)

    async def list_active(self, *, skip: int = 0, limit: int = 100) -> Sequence[User]:
        """Return only active users, paginated."""
        stmt = select(User).where(User.is_active.is_(True)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ---------- Mutators ----------

    async def set_active(self, user: User, *, is_active: bool) -> User:
        """Toggle the `is_active` flag."""
        return await self.update(user, {"is_active": is_active})

    async def set_verified(self, user: User, *, is_verified: bool) -> User:
        """Toggle the `is_verified` flag."""
        return await self.update(user, {"is_verified": is_verified})
