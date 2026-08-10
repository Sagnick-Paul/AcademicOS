"""Domain exceptions for the chat/conversation layer.

HTTP-agnostic, follows the existing service-exception conventions:
the endpoint layer translates them into ``HTTPException`` responses
without leaking internal details.
"""
from __future__ import annotations

from uuid import UUID


class ChatError(Exception):
    """Base class for all chat-service errors."""


class ChatSessionNotFoundError(ChatError):
    """Raised when a session lookup misses — either no such id exists
    or it belongs to a different user.

    The two cases are deliberately indistinguishable to callers. The
    endpoint layer translates this to a 404 so a request cannot be
    used to enumerate session ids belonging to other users.
    """

    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Chat session {session_id!r} not found")
        self.session_id = session_id


class ChatMessageEmptyError(ChatError):
    """Raised when a user submits a blank/empty message."""

    def __init__(self) -> None:
        super().__init__("Message content cannot be empty")


class ChatSessionTitleError(ChatError):
    """Raised when a session title cannot be derived from a query."""


__all__ = [
    "ChatError",
    "ChatMessageEmptyError",
    "ChatSessionNotFoundError",
    "ChatSessionTitleError",
]
