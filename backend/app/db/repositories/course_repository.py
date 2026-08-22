"""Course repository.

Per-owner listing and ownership-scoped lookups live here. Storage I/O
is the job of `app.storage`, not this module.
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.course import Course
from app.db.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    """Async repository for :class:`app.db.models.course.Course`."""

    model = Course

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ---------- Lookups ----------

    async def get_for_owner(
        self,
        course_id: UUID | str,
        *,
        owner_id: UUID | str,
    ) -> Course | None:
        """Look up a course scoped to an owner.

        The owner filter is part of the query itself rather than a
        post-filter so the endpoint cannot be tricked by guessing an
        id that belongs to a different user.
        """
        stmt = select(Course).where(
            Course.id == course_id,
            Course.owner_id == owner_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_owner(
        self,
        owner_id: UUID | str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Course]:
        """List courses belonging to a specific user, most-recent first.

        Ordering matches the project convention (newest activity first)
        and is tied by ``id`` to keep results deterministic when two
        rows share the same ``updated_at`` timestamp.
        """
        stmt = (
            select(Course)
            .where(Course.owner_id == owner_id)
            .order_by(Course.updated_at.desc(), Course.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def exists_for_owner(
        self,
        *,
        owner_id: UUID | str,
        name: str,
        exclude_id: UUID | str | None = None,
    ) -> bool:
        """Return True if the owner already has a course with this name.

        When ``exclude_id`` is provided, that row is ignored — useful
        for updates where keeping the same name is allowed but a
        separate collision must still raise.
        """
        stmt = select(Course.id).where(
            Course.owner_id == owner_id,
            Course.name == name,
        )
        if exclude_id is not None:
            stmt = stmt.where(Course.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ---------- Mutators ----------

    async def rename(
        self,
        course: Course,
        *,
        name: str,
    ) -> Course:
        """Update a course's name."""
        return await self.update(course, {"name": name})
