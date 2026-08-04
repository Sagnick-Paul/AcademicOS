"""Authentication service.

All authentication logic lives here: registration, credential check,
token issuance, and current-user lookup. Endpoints are thin wrappers
that translate domain exceptions to HTTP errors and ORM objects to
response schemas.

The flow is always:

    Endpoint → AuthService → UserRepository → Database

Endpoints must not call the repository directly, and the service must
not raise ``HTTPException`` (domain exceptions only).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.core.security import InvalidTokenError
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
)


# Pre-computed bcrypt hash of an arbitrary value used to keep response
# times constant on the unknown-email path of ``authenticate``. Without
# this, an attacker could enumerate registered emails by timing the
# difference between "no bcrypt run" (unknown email) and "bcrypt run"
# (known email).
_DUMMY_HASH = hash_password("not-a-real-password-1234567890")


class AuthService:
    """Encapsulates registration, authentication, and current-user lookup."""

    def __init__(
        self,
        session: AsyncSession,
        # Settings is accepted for symmetry with other services even though
        # no method currently needs it. It documents the dependency and
        # keeps tests from having to swap the dep later.
        settings: Settings | None = None,  # noqa: ARG002 - reserved
    ) -> None:
        self.session = session
        self.repo = UserRepository(session)

    # ---------- Registration ----------

    async def register(self, payload: UserCreate) -> User:
        """Create a new user.

        Raises:
            EmailAlreadyExistsError: the email is already in use.
                Caught at the unique-constraint level so concurrent
                registrations don't slip through a check-then-insert race.
        """
        user = User(
            full_name=payload.full_name,
            email=payload.email,
            hashed_password=hash_password(payload.password),
        )
        try:
            return await self.repo.create(user)
        except IntegrityError as exc:
            await self.session.rollback()
            raise EmailAlreadyExistsError(
                f"Email {payload.email!r} is already registered"
            ) from exc

    # ---------- Authentication ----------

    async def authenticate(self, email: str, password: str) -> User:
        """Verify email + password and return the active user.

        Raises:
            InvalidCredentialsError: unknown email or wrong password.
                The two cases are deliberately indistinguishable to the
                caller to prevent email enumeration.
            InactiveUserError: credentials are valid but the account is
                disabled.
        """
        user = await self.repo.get_by_email(email)

        if user is None:
            # Equalize timing with the known-email path. The result is
            # discarded; only the wall-clock cost matters.
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentialsError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            raise InactiveUserError("Account is inactive")

        return user

    async def login(self, payload: LoginRequest) -> TokenResponse:
        """Authenticate and issue a bearer token."""
        user = await self.authenticate(payload.email, payload.password)
        token = create_access_token(subject=user.id)
        return TokenResponse(access_token=token)

    # ---------- Current user ----------

    async def get_user_by_token(self, token: str) -> User:
        """Resolve a JWT to its owning user.

        Raises:
            InvalidTokenError: the token is malformed, has a bad
                signature, is expired, or refers to a user that no
                longer exists. ``ExpiredTokenError`` is a subclass and
                will be caught by handlers looking specifically for it.
        """
        claims = verify_token(token)  # raises InvalidTokenError / ExpiredTokenError

        sub = claims.get("sub")
        if not sub:
            raise InvalidTokenError("Token missing subject claim")

        try:
            user_id = UUID(str(sub))
        except (ValueError, TypeError) as exc:
            raise InvalidTokenError("Token subject is not a valid UUID") from exc

        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise InvalidTokenError("User no longer exists")

        return user
