"""Course endpoints.

Five thin handlers: list, create, get, update, delete. Business logic
lives in :class:`app.services.course_service.CourseService`; this
module only translates domain exceptions into HTTP responses and
commits the session after writes that must be visible to subsequent
requests.

Every endpoint requires an authenticated user. Ownership is enforced
inside the service / repository layer — never trust ``owner_id`` from
the wire.
"""
from __future__ import annotations

from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Response, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

# pyrefly: ignore [missing-import]
from app.api.deps import get_course_service, get_current_active_user
from app.db.models.user import User
from app.schemas.course import (
    CourseCreate,
    CourseListResponse,
    CourseResponse,
    CourseUpdate,
)
from app.services.course_service import CourseService
from app.services.exceptions import (
    CourseNotFoundError,
    DuplicateCourseNameError,
)


router = APIRouter()


# ---------- helpers ----------


async def _commit(session: AsyncSession) -> None:
    """Commit the current session. Duplicated from other endpoints
    deliberately so each endpoint module stays self-contained.
    """
    await session.commit()


# ---------- endpoints ----------


@router.get(
    "",
    response_model=CourseListResponse,
    summary="List the current user's courses",
)
async def list_my_courses(
    current: User = Depends(get_current_active_user),
    service: CourseService = Depends(get_course_service),
    skip: int = 0,
    limit: int = 100,
) -> CourseListResponse:
    """Return the authenticated user's courses, most-recently-active first."""
    rows = await service.list_user_courses(
        owner_id=current.id, skip=skip, limit=limit
    )
    return CourseListResponse(
        items=[CourseResponse.model_validate(r) for r in rows]
    )


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course",
)
async def create_course(
    payload: CourseCreate,
    current: User = Depends(get_current_active_user),
    service: CourseService = Depends(get_course_service),
) -> CourseResponse:
    """Create a course owned by the authenticated user.

    ``owner_id`` is derived from the bearer token, never from the
    payload. Returns 409 when the owner already has a course with
    the requested name.
    """
    try:
        course = await service.create_course(owner=current, payload=payload)
    except DuplicateCourseNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from None

    await _commit(service.session)
    return CourseResponse.model_validate(course)


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Get a single course",
)
async def get_my_course(
    course_id: UUID,
    current: User = Depends(get_current_active_user),
    service: CourseService = Depends(get_course_service),
) -> CourseResponse:
    """Return metadata for a course owned by the authenticated user.

    Returns 404 for both missing IDs and IDs owned by another user so
    that the endpoint cannot be used to enumerate other users'
    course ids.
    """
    try:
        course = await service.get_course_for_owner(
            course_id=course_id, owner_id=current.id
        )
    except CourseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        ) from None
    return CourseResponse.model_validate(course)


@router.patch(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Update a course",
)
async def update_my_course(
    course_id: UUID,
    payload: CourseUpdate,
    current: User = Depends(get_current_active_user),
    service: CourseService = Depends(get_course_service),
) -> CourseResponse:
    """Apply a partial update to a course owned by the authenticated user.

    Clients cannot change ``owner_id``, ``id``, ``created_at``, or
    ``updated_at`` — the update schema rejects unknown fields.

    Returns 404 for missing or not-owned courses; 409 when the new
    name collides with another of the caller's courses.
    """
    try:
        course = await service.update_course(
            course_id=course_id,
            owner_id=current.id,
            payload=payload,
        )
    except CourseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        ) from None
    except DuplicateCourseNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from None

    await _commit(service.session)
    return CourseResponse.model_validate(course)


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a course",
)
async def delete_my_course(
    course_id: UUID,
    current: User = Depends(get_current_active_user),
    service: CourseService = Depends(get_course_service),
) -> Response:
    """Delete a course owned by the authenticated user.

    Returns 404 for missing or not-owned courses (same as GET). 204
    No Content on success.
    """
    try:
        await service.delete_course(course_id=course_id, owner_id=current.id)
    except CourseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        ) from None
    await _commit(service.session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
