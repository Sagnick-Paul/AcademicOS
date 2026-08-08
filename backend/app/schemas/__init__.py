"""Pydantic schemas: request/response DTOs.

Separate from ORM models so the wire format can evolve independently.
Organize by aggregate (e.g. `user.py`, `document.py`).
"""
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
)
from app.schemas.user import (
    UserCreate,
    UserInDB,
    UserResponse,
    UserUpdate,
)
from app.schemas.search import (
    SearchRequest,
    RetrievedChunk,
    SearchResponse,
)

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    "LoginRequest",
    "TokenResponse",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "ChatSessionCreate",
    "ChatSessionUpdate",
    "ChatSessionResponse",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "SearchRequest",
    "RetrievedChunk",
    "SearchResponse",
]
