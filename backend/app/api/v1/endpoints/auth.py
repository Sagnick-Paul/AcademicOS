"""Authentication endpoints.

Three thin handlers: register, login, current user. All business logic
lives in :class:`app.services.auth_service.AuthService`; this module
only translates between HTTP and the service layer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_service, get_current_active_user
from app.db.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
)


router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserCreate,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Create a new AcademicOS account."""
    try:
        user = await service.register(payload)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        ) from None

    # Service commits via repository; ensure the new user is visible to
    # subsequent requests on the same session.
    await _commit(service.session)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in and obtain a JWT access token",
)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Exchange email + password for a bearer token.

    Bad credentials and unknown emails return the same response body so
    an attacker cannot enumerate registered emails.
    """
    try:
        return await service.login(payload)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        ) from None
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        ) from None


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the currently authenticated user",
)
async def read_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Return the user identified by the bearer token."""
    return UserResponse.model_validate(current_user)


# ---------- helpers ----------


async def _commit(session: AsyncSession) -> None:
    """Commit the current session, swallowing nothing.

    Lives in the endpoint layer because the service is HTTP-agnostic.
    """
    await session.commit()
