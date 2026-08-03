"""Pydantic schemas for :class:`app.db.models.user.User`.

- ``UserCreate`` — payload for registration
- ``UserUpdate`` — partial update; every field optional
- ``UserResponse`` — public-facing representation
- ``UserInDB`` — internal record including the password hash
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# Constraints are declared once and reused.
NameStr = Annotated[str, Field(min_length=1, max_length=255)]


class UserBase(BaseModel):
    """Shared user fields."""

    full_name: NameStr
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        """Lowercase emails so uniqueness checks are case-insensitive."""
        if isinstance(value, str):
            return value.strip().lower()
        return value


class UserCreate(UserBase):
    """Payload to create a new user. The plaintext password is hashed by
    the service layer before persistence; the repository never sees it."""

    password: Annotated[str, Field(min_length=8, max_length=128)]


class UserUpdate(BaseModel):
    """Partial update. Any field omitted is left untouched."""

    model_config = ConfigDict(extra="forbid")

    full_name: NameStr | None = None
    email: EmailStr | None = None
    password: Annotated[str, Field(min_length=8, max_length=128)] | None = None
    is_active: bool | None = None
    is_verified: bool | None = None


class UserResponse(UserBase):
    """Public user representation. No password material here."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserInDB(UserResponse):
    """Internal representation, includes the stored password hash."""

    hashed_password: str
