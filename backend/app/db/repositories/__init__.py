"""Repository pattern: data-access layer.

Encapsulate queries here so services and endpoints remain orchestration-
only. One module per aggregate, mirroring the models package.
"""
from app.db.repositories.base import BaseRepository
from app.db.repositories.chat_repository import (
    ChatMessageRepository,
    ChatSessionRepository,
)
from app.db.repositories.course_repository import CourseRepository
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "DocumentRepository",
    "CourseRepository",
    "ChatSessionRepository",
    "ChatMessageRepository",
]
