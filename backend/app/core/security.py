"""Security helpers: password hashing, JWT encode/decode/verify.

Custom exception types (``InvalidTokenError`` / ``ExpiredTokenError``) let
callers distinguish failure modes without coupling to HTTP. The FastAPI
boundary in :mod:`app.api.deps` is responsible for translating them into
``HTTPException`` responses.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# Password hashing context (bcrypt). Reuse across the app.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- Exceptions ----------


class InvalidTokenError(Exception):
    """Raised when a JWT is malformed, has a bad signature, or is otherwise
    unparseable. Also raised when the token has no ``exp`` claim."""


class ExpiredTokenError(InvalidTokenError):
    """Raised when a JWT is well-formed but its ``exp`` claim is in the past."""


# ---------- Passwords ----------


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------- JWT ----------


def create_access_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    The subject is coerced to ``str`` so UUIDs (and other primitive types)
    can be passed directly.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode a JWT access token, returning the payload or None on failure.

    Soft-fail variant — prefer :func:`verify_token` in code paths that need
    to distinguish failure modes.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def verify_token(token: str) -> dict[str, Any]:
    """Verify a JWT and return its claims.

    Raises:
        ExpiredTokenError: token was valid but has expired.
        InvalidTokenError: token is malformed, has a bad signature, or
            is missing the ``exp`` claim.

    The ``exp`` claim is required so a token without one is rejected
    outright rather than accepted forever.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require_exp": True},
        )
    except ExpiredSignatureError as exc:
        raise ExpiredTokenError("Token has expired") from exc
    except JWTError as exc:
        raise InvalidTokenError("Could not validate credentials") from exc
