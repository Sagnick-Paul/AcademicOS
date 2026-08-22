"""Course service.

Owns:

* validating course payloads (in addition to Pydantic-level checks)
* enforcing per-user uniqueness on course name
* enforcing ownership on every read / update / delete

The endpoint layer is thin — it calls the service, translates domain
exceptions into HTTP responses, and commits the session. No business
logic lives outside this module.
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID

# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.course import Course
from app.db.models.user import User
from app.db.repositories.course_repository import CourseRepository
from app.schemas.course import CourseCreate, CourseUpdate
from app.services.exceptions import (
    CourseNotFoundError,
    DuplicateCourseNameError,
)


class CourseService:
    """Orchestrates course create / read / update / delete operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CourseRepository(session)
        self.logger = get_logger(__name__)

    # ---------- helpers ----------

    @staticmethod
    def _normalize_optional(value: str | None) -> str | None:
        """Trim optional text. ``None`` and empty-after-trim both → ``None``."""
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _require_name(value: str | None) -> str:
        """Trim and require non-empty name."""
        assert value is not None  # Pydantic guards this upstream
        trimmed = value.strip()
        if not trimmed:
            # Defensive: Pydantic should have caught this already.
            raise DuplicateCourseNameError(value)
        return trimmed

    # ---------- Create ----------

    async def create_course(
        self,
        *,
        owner: User,
        payload: CourseCreate,
    ) -> Course:
        """Create a course owned by ``owner``.

        Raises:
            DuplicateCourseNameError: the owner already has a course
                with this name.
        """
        name = self._require_name(payload.name)
        code = self._normalize_optional(payload.code)
        description = self._normalize_optional(payload.description)

        if await self.repo.exists_for_owner(owner_id=owner.id, name=name):
            raise DuplicateCourseNameError(name)

        course = Course(
            owner_id=owner.id,
            name=name,
            code=code,
            description=description,
        )
        course = await self.repo.create(course)

        self.logger.info(
            "course.created id=%s owner=%s name=%s",
            course.id,
            owner.id,
            name,
        )
        return course

    # ---------- Listing ----------

    async def list_user_courses(
        self,
        *,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Course]:
        """Return the caller's courses, most-recently-active first."""
        return await self.repo.list_for_owner(owner_id, skip=skip, limit=limit)

    # ---------- Fetch (ownership-enforced) ----------

    async def get_course_for_owner(
        self,
        *,
        course_id: UUID,
        owner_id: UUID,
    ) -> Course:
        """Look up a course and verify ownership.

        Raises:
            CourseNotFoundError: missing id, *or* owned by someone else.
                The endpoint must respond with 404 in both cases.
        """
        course = await self.repo.get_for_owner(course_id, owner_id=owner_id)
        if course is None:
            raise CourseNotFoundError(course_id)
        return course

    # ---------- Update ----------

    async def update_course(
        self,
        *,
        course_id: UUID,
        owner_id: UUID,
        payload: CourseUpdate,
    ) -> Course:
        """Apply a partial update to a course owned by ``owner_id``.

        Uniqueness is re-checked when ``name`` changes. Fields left
        ``None`` are left untouched.

        Raises:
            CourseNotFoundError: missing or not-owned.
            DuplicateCourseNameError: the new name collides with one
                of the owner's existing courses.
        """
        course = await self.get_course_for_owner(
            course_id=course_id, owner_id=owner_id
        )

        updates: dict[str, object] = {}

        if payload.name is not None:
            new_name = self._require_name(payload.name)
            if new_name != course.name and await self.repo.exists_for_owner(
                owner_id=owner_id,
                name=new_name,
                exclude_id=course.id,
            ):
                raise DuplicateCourseNameError(new_name)
            updates["name"] = new_name

        if payload.code is not None:
            updates["code"] = self._normalize_optional(payload.code)

        if payload.description is not None:
            updates["description"] = self._normalize_optional(payload.description)

        if not updates:
            return course

        course = await self.repo.update(course, updates)
        self.logger.info(
            "course.updated id=%s owner=%s fields=%s",
            course.id,
            owner_id,
            sorted(updates.keys()),
        )
        return course

    # ---------- Delete ----------

    async def delete_course(
        self,
        *,
        course_id: UUID,
        owner_id: UUID,
    ) -> None:
        """Delete a course owned by ``owner_id``.

        Phase 6A intentionally has no cascading to documents because
        the Document ↔ Course link does not exist yet.

        Raises:
            CourseNotFoundError: missing or not-owned.
        """
        course = await self.get_course_for_owner(
            course_id=course_id, owner_id=owner_id
        )
        await self.repo.delete(course)
        self.logger.info(
            "course.deleted id=%s owner=%s",
            course.id,
            owner_id,
        )
