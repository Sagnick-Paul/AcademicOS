"""Pydantic schemas for chat sessions and messages.

Keeps the wire format independent of the ORM layer.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import ChatRole


TitleStr = Annotated[str, Field(min_length=1, max_length=255)]


# ---------- ChatSession ----------


class ChatSessionBase(BaseModel):
    """Shared fields for a chat session."""

    title: TitleStr = "New chat"


class ChatSessionCreate(ChatSessionBase):
    """Payload for creating a chat session. `user_id` is set from auth."""


class ChatSessionUpdate(BaseModel):
    """Partial update — typically renaming a session."""

    model_config = ConfigDict(extra="forbid")

    title: TitleStr | None = None


class ChatSessionResponse(ChatSessionBase):
    """Public chat session representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


# ---------- ChatMessage ----------


class ChatMessageBase(BaseModel):
    """Shared fields for a chat message."""

    role: ChatRole
    content: Annotated[str, Field(min_length=1)]


class ChatMessageCreate(ChatMessageBase):
    """Payload for creating a chat message. `session_id` is set by the
    service layer from the URL, not by the client."""


class ChatMessageResponse(ChatMessageBase):
    """Public chat message representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    created_at: datetime
