"""RAG-backed chat endpoint.

Exposes the chat surface:

* ``POST /api/v1/chat`` — one-shot RAG (kept for backward compatibility).
* ``POST /api/v1/chat/sessions`` — create a session.
* ``GET  /api/v1/chat/sessions`` — list the caller's sessions.
* ``GET  /api/v1/chat/sessions/{session_id}`` — retrieve a session.
* ``DELETE /api/v1/chat/sessions/{session_id}`` — delete a session.
* ``POST /api/v1/chat/sessions/{session_id}/messages`` — send a
  message in a session.

All session/message endpoints enforce ownership at the service layer
and surface 404 (not 403) for cross-user access.
"""
from __future__ import annotations

import uuid
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from app.api.deps import (
    get_chat_service,
    get_current_active_user,
    get_document_service,
    get_rag_service,
)
from app.db.models.chat import ChatSession
from app.db.models.user import User
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMError,
    LLMProviderUnavailable,
    LLMRequestRejected,
    LLMResponseInvalid,
)
from app.rag.exceptions import (
    DocumentAccessDeniedError,
    NoRelevantContextError,
)
from app.rag.service import RAGService
from app.schemas.chat import (
    ChatMessageResponse,
    ChatMessageSourceResponse,
    ChatMessageWithSourcesResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
    ChatSessionWithMessagesResponse,
    ChatSource,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.chat_exceptions import (
    ChatMessageEmptyError,
    ChatSessionNotFoundError,
)
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.exceptions import CourseNotFoundError, DocumentNotFoundError

router = APIRouter()

_NO_CONTEXT_MESSAGE = (
    "I cannot answer this based on the provided documents."
)


def _http_for_llm_error(exc: LLMError) -> HTTPException:
    """Translate LLMError subclasses into HTTP responses with safe details."""
    if isinstance(exc, LLMConfigurationError):
        return HTTPException(
            status_code=503,
            detail="The chat service is not configured. Please contact support.",
        )
    if isinstance(exc, (LLMProviderUnavailable, LLMResponseInvalid)):
        return HTTPException(
            status_code=503,
            detail="The chat service is temporarily unavailable. Please try again.",
        )
    return HTTPException(
        status_code=503,
        detail="The chat service rejected the request. Please try again.",
    )


def _session_to_response(sess: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse.model_validate(sess)


def _session_with_messages(
    sess: ChatSession,
    *,
    messages: list,
) -> ChatSessionWithMessagesResponse:
    msg_dtos: list[ChatMessageWithSourcesResponse] = []
    for msg in messages:
        sources = [
            ChatMessageSourceResponse.model_validate(s)
            for s in (msg.sources or [])
        ]
        msg_dtos.append(
            ChatMessageWithSourcesResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                sources=sources,
            )
        )
    return ChatSessionWithMessagesResponse(
        id=sess.id,
        user_id=sess.user_id,
        title=sess.title,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
        messages=msg_dtos,
    )


# ─────────────────────────────────────────────────────────────────────────────
# One-shot RAG (Phase 2 Step 5) — preserved for backward compatibility
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question grounded in your documents (one-shot)",
)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    rag_service: RAGService = Depends(get_rag_service),
    document_service: DocumentService = Depends(get_document_service),
) -> ChatResponse:
    """Run the RAG pipeline and return the answer plus structured sources."""
    if request.document_id is not None:
        try:
            await document_service.get_document_for_owner(
                document_id=request.document_id,
                owner_id=current_user.id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            ) from exc

    try:
        answer = await rag_service.answer_question(
            query=request.query,
            owner_id=current_user.id,
            document_id=request.document_id,
            mode=request.mode,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )
    except NoRelevantContextError:
        return ChatResponse(
            answer=_NO_CONTEXT_MESSAGE,
            sources=[],
            model="(no-model)",
            retrieval_mode=request.mode,
        )
    except DocumentAccessDeniedError:
        raise HTTPException(
            status_code=404, detail="Document not found",
        ) from None
    except LLMError as exc:
        raise _http_for_llm_error(exc) from exc

    sources: list[ChatSource] = []
    for src in answer.sources:
        title: str | None = None
        if src.document_id is not None:
            try:
                doc = await document_service.get_document_for_owner(
                    document_id=src.document_id,
                    owner_id=current_user.id,
                )
                title = doc.original_filename
            except Exception:
                title = None
        sources.append(
            ChatSource(
                index=src.index,
                chunk_id=src.chunk_id,
                document_id=src.document_id,
                document_title=title,
                page_number=src.page_number,
                chunk_index=src.chunk_index,
                score=src.score,
                snippet=src.snippet,
            )
        )

    return ChatResponse(
        answer=answer.answer,
        sources=sources,
        model=answer.model,
        retrieval_mode=answer.retrieval_mode,
        prompt_tokens=answer.prompt_tokens,
        completion_tokens=answer.completion_tokens,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Session-based endpoints (Phase 3)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    """Create a session for the authenticated user.

    Optionally accepts an ``initial_query`` that is persisted as the
    first user message; the assistant reply is *not* generated here.
    ``course_id`` (Phase 6B) optionally attaches the new session to
    a course owned by the caller — a missing or foreign course id
    returns 404.
    """
    try:
        sess = await chat_service.create_session(
            owner=current_user,
            title=payload.title,
            initial_query=payload.initial_query,
            course_id=payload.course_id,
            document_id=payload.document_id,
        )
    except ChatMessageEmptyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _session_to_response(sess)


@router.get(
    "/sessions",
    response_model=list[ChatSessionResponse],
    summary="List the caller's chat sessions",
)
async def list_sessions(
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
    course_id: UUID | None = None,
) -> list[ChatSessionResponse]:
    """List sessions owned by the authenticated user, newest first.

    Phase 6B: ``?course_id=<uuid>`` filters to sessions belonging to
    the named course. The course must be owned by the caller — a
    foreign or missing course id returns 404.
    """
    try:
        sessions = await chat_service.list_user_sessions(
            owner_id=current_user.id, course_id=course_id,
        )
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_session_to_response(s) for s in sessions]


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionWithMessagesResponse,
    summary="Retrieve a chat session and its history",
)
async def get_session(
    session_id: UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatSessionWithMessagesResponse:
    """Fetch a session owned by the caller, including all messages."""
    try:
        sess = await chat_service.get_session_with_messages(
            session_id=session_id, owner_id=current_user.id,
        )
        messages = list(sess.messages)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat session not found") from exc
    return _session_with_messages(sess, messages=messages)


@router.patch(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="Update a chat session",
)
async def update_session(
    payload: ChatSessionUpdate,
    session_id: UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    """Update a session's title and/or course link. Owner-only.

    Phase 6B: ``course_id`` may be ``null`` (unlink) or a UUID the
    caller owns. A foreign or missing course id returns 404.
    """
    try:
        sess = await chat_service.update_session(
            session_id=session_id,
            owner_id=current_user.id,
            title=payload.title,
            course_id=payload.course_id,
            set_course="course_id" in payload.model_fields_set,
        )
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat session not found") from exc
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _session_to_response(sess)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a chat session",
)
async def delete_session(
    session_id: UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> Response:
    """Delete a session and all its messages. Owner-only."""
    try:
        await chat_service.delete_session(
            session_id=session_id, owner_id=current_user.id,
        )
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat session not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=SendMessageResponse,
    summary="Send a message into a chat session",
)
async def send_message(
    payload: SendMessageRequest,
    session_id: UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
    document_service: DocumentService = Depends(get_document_service),
) -> SendMessageResponse:
    """Persist the user question, call RAG, persist the assistant reply.

    Errors:

    * 401 — missing/invalid token.
    * 404 — session not found or owned by another user, OR document
      not owned by the caller.
    * 422 — empty ``query``.
    * 503 — LLM-side failure (never leaks provider details).
    """
    try:
        result = await chat_service.send_message(
            session_id=session_id,
            owner_id=current_user.id,
            query=payload.query,
            document_id=payload.document_id,
            mode=payload.mode,
            top_k=payload.top_k,
            score_threshold=payload.score_threshold,
            temperature=payload.temperature,
            max_output_tokens=payload.max_output_tokens,
        )
    except ChatMessageEmptyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat session not found") from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    except NoRelevantContextError:
        # Should be caught inside the service, but defend anyway.
        raise HTTPException(
            status_code=200,
            detail="No relevant context",
        ) from None
    except LLMError as exc:
        raise _http_for_llm_error(exc) from exc

    # Build the response with resolved document titles.
    titles: dict = {}
    for src in result.sources:
        if src.document_id is None:
            continue
        try:
            doc = await document_service.get_document_for_owner(
                document_id=src.document_id,
                owner_id=current_user.id,
            )
            titles[src.document_id] = doc.original_filename
        except Exception:
            titles[src.document_id] = None

    sources: list[ChatMessageSourceResponse] = []
    for src in result.sources:
        # Build a stable UUID for the wire shape. Real persisted rows
        # have a database id; in the response we surface the persisted
        # row's id (same shape, different value) so the client doesn't
        # need two types of source DTO.
        sources.append(
            ChatMessageSourceResponse(
                id=_ephemeral_id(src),
                message_id=result.assistant_message.id,
                document_id=src.document_id or result.assistant_message.id,
                chunk_id=src.chunk_id,
                position=src.index,
                page_number=src.page_number,
                slide_number=None,
                score=src.score,
                snippet=src.snippet,
            )
        )

    user_msg = ChatMessageResponse.model_validate(result.user_message)
    assistant_msg = ChatMessageWithSourcesResponse(
        id=result.assistant_message.id,
        session_id=result.assistant_message.session_id,
        role=result.assistant_message.role,
        content=result.assistant_message.content,
        created_at=result.assistant_message.created_at,
        sources=sources,
    )

    return SendMessageResponse(
        user_message=user_msg,
        assistant_message=assistant_msg,
        model=result.rag_answer.model,
        retrieval_mode=result.rag_answer.retrieval_mode,
        prompt_tokens=result.rag_answer.prompt_tokens,
        completion_tokens=result.rag_answer.completion_tokens,
    )


def _ephemeral_id(src) -> UUID:  # pragma: no cover - tiny helper
    """Return a deterministic UUID derived from a ChatSource.

    Used only for the ephemeral source rows returned in the message
    response. The actual persisted rows have a real database id; we
    surface those when available.
    """
    seed = f"{src.chunk_id}:{src.index}"
    return uuid.uuid5(uuid.NAMESPACE_URL, seed)