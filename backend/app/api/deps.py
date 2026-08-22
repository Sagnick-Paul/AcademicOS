"""Shared FastAPI dependencies.

Common ``Depends(...)`` callables: DB session, settings, repositories,
services, and the current-user resolver used by protected endpoints.
Implementations land here as features are added.
"""
from __future__ import annotations

from typing import AsyncGenerator

# pyrefly: ignore [missing-import]
from fastapi import Depends, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.security import OAuth2PasswordBearer
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

# pyrefly: ignore [missing-import]
from app.core.config import Settings, get_settings
# pyrefly: ignore [missing-import]
from app.core.security import ExpiredTokenError, InvalidTokenError
# pyrefly: ignore [missing-import]
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_db
from app.services.auth_service import AuthService
from app.services.course_service import CourseService
from app.services.document_service import DocumentService
from app.services.retrieval_service import RetrievalService


__all__ = [
    "get_db",
    "get_settings",
    "get_settings_dep",
    "get_user_repository",
    "get_auth_service",
    "get_document_service",
    "get_course_service",
    "get_retrieval_service",
    "get_rag_service",
    "get_chat_service",
    "get_current_user",
    "get_current_active_user",
]



# ---------- Settings ----------


def get_settings_dep() -> Settings:
    """Settings dependency wrapper for ``Depends(...)``."""
    return get_settings()


# Type aliases for clean signatures in endpoints.
DBSession = AsyncSession
SettingsDep = Depends(get_settings_dep)


async def _db_session_dep() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


DBDep = Depends(_db_session_dep)


# ---------- OAuth2 / Bearer ----------


# `auto_error=False` so we control the 401 body. The tokenUrl is what
# Swagger displays in the Authorize dialog; the endpoint does not need
# to be reachable for the dialog to render.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


# ---------- Repository / service providers ----------


def get_user_repository(
    session: AsyncSession = Depends(_db_session_dep),
) -> UserRepository:
    """FastAPI dependency yielding a fresh :class:`UserRepository`."""
    return UserRepository(session)


def get_auth_service(
    session: AsyncSession = Depends(_db_session_dep),
    settings: Settings = Depends(get_settings_dep),
) -> AuthService:
    """FastAPI dependency yielding a fresh :class:`AuthService`."""
    return AuthService(session, settings)


def get_document_service(
    session: AsyncSession = Depends(_db_session_dep),
) -> DocumentService:
    """FastAPI dependency yielding a fresh :class:`DocumentService`."""
    return DocumentService(session)


def get_course_service(
    session: AsyncSession = Depends(_db_session_dep),
) -> CourseService:
    """FastAPI dependency yielding a fresh :class:`CourseService`."""
    return CourseService(session)


def get_retrieval_service() -> RetrievalService:
    """FastAPI dependency yielding a fresh :class:`RetrievalService`."""
    from app.processing.embeddings.provider import SentenceTransformerEmbeddingProvider
    from app.processing.embeddings.qdrant import QdrantVectorStore

    provider = SentenceTransformerEmbeddingProvider()
    vector_store = QdrantVectorStore()
    return RetrievalService(embedding_provider=provider, vector_store=vector_store)


def get_rag_service(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> "RAGService":
    """FastAPI dependency yielding a fresh :class:`RAGService`."""
    # Local import to avoid an import cycle (rag -> services -> rag) and
    # to keep test imports lightweight.
    from app.llm.provider import get_llm_provider
    from app.rag.service import RAGService

    llm_provider = get_llm_provider()
    return RAGService(
        retrieval_service=retrieval_service,
        llm_provider=llm_provider,
    )


def get_chat_service(
    session: AsyncSession = Depends(_db_session_dep),
    rag_service: "RAGService" = Depends(get_rag_service),
) -> "ChatService":
    """FastAPI dependency yielding a fresh :class:`ChatService`."""
    from app.services.chat_service import ChatService

    return ChatService(session=session, rag_service=rag_service)



# ---------- Current user ----------


_BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """Resolve the bearer token in the ``Authorization`` header to a user.

    Raises:
        HTTPException 401: missing token, malformed token, bad
            signature, or expired token. Expired vs. malformed are
            distinguished by the ``detail`` field.
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers=_BEARER_CHALLENGE,
        )
    try:
        return await service.get_user_by_token(token)
    except ExpiredTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers=_BEARER_CHALLENGE,
        ) from None
    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers=_BEARER_CHALLENGE,
        ) from None


async def get_current_active_user(
    current: User = Depends(get_current_user),
) -> User:
    """Like :func:`get_current_user`, but rejects inactive accounts.

    Raises:
        HTTPException 403: the token is valid but the user has been
            deactivated.
    """
    if not current.is_active:
        raise HTTPException(
            status_code=403,
            detail="Inactive account",
        )
    return current
