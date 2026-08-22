"""ORM models for AcademicOS.

Importing this package registers every model on `Base.metadata` so that
Alembic autogenerate and `Base.metadata.create_all` see all tables.
"""
from app.db.models.chat import ChatMessage, ChatMessageSource, ChatSession
from app.db.models.course import Course
from app.db.models.document import Document
from app.db.models.enums import ChatRole, DocumentType, DocumentUploadStatus
from app.db.models.user import User

__all__ = [
    "User",
    "Document",
    "Course",
    "ChatSession",
    "ChatMessage",
    "ChatMessageSource",
    "ChatRole",
    "DocumentType",
    "DocumentUploadStatus",
]
