"""Generic async repository for SQLAlchemy ORM models.

Encapsulates the boilerplate of CRUD on a single model. Concrete
repositories inherit and add aggregate-specific queries. No business
logic lives here — only data access.
"""
from __future__ import annotations

from typing import Any, Generic, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Common async CRUD operations for a single ORM model.

    Subclasses set :attr:`model` to the concrete ORM class.
    """

    model: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------- Create ----------

    async def create(self, obj: ModelT) -> ModelT:
        """Persist a new instance. Flushes so caller sees PKs."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    # ---------- Read ----------

    async def get_by_id(
        self, obj_id: UUID | str, *, raise_if_missing: bool = False
    ) -> ModelT | None:
        """Look up by primary key. Optionally raise if not found."""
        result = await self.session.get(self.model, obj_id)
        if result is None and raise_if_missing:
            raise LookupError(f"{self.model.__name__} {obj_id!r} not found")
        return result

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        """List rows with offset/limit pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ---------- Update ----------

    async def update(
        self,
        obj: ModelT,
        values: dict[str, Any],
    ) -> ModelT:
        """Apply a dict of column updates to an instance and persist."""
        for key, value in values.items():
            if not hasattr(obj, key):
                raise AttributeError(
                    f"{self.model.__name__} has no attribute {key!r}"
                )
            setattr(obj, key, value)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    # ---------- Delete ----------

    async def delete(self, obj: ModelT) -> None:
        """Delete an instance via the session."""
        await self.session.delete(obj)
        await self.session.flush()

    async def delete_by_id(self, obj_id: UUID | str) -> bool:
        """Bulk delete by primary key. Returns True if a row was removed."""
        stmt = sa_delete(self.model).where(self.model.id == obj_id)
        result = await self.session.execute(stmt)
        return (result.rowcount or 0) > 0
