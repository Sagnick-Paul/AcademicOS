"""Pydantic schemas for the authentication endpoints.

- ``LoginRequest`` — payload for ``POST /auth/login``
- ``TokenResponse`` — response shape for both login and any future token
  issuance endpoint

The decoded JWT is intentionally not represented as a pydantic model: it
stays an untyped ``dict[str, Any]`` until ``verify_token`` has vouched for
it, and round-tripping through pydantic on every request would be wasted
work. Type hints in :mod:`app.services.auth_service` are sufficient.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Payload for ``POST /auth/login``.

    Email is normalized (stripped + lowercased) at the boundary so the
    service can compare directly against the stored value.
    """

    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class TokenResponse(BaseModel):
    """Response shape for any endpoint that issues a bearer token."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
