"""Pydantic schemas for chat sessions and messages.

Keeps the wire format independent of the ORM layer.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models.enums import ChatRole


TitleStr = Annotated[str, Field(min_length=1, max_length=255)]


# ---------- ChatSession ----------


class ChatSessionBase(BaseModel):
    """Shared fields for a chat session."""

    title: TitleStr = "New chat"


class ChatSessionCreate(ChatSessionBase):
    """Payload for creating a chat session. `user_id` is set from auth.

    Phase 6B: ``course_id`` is an optional course to attach this
    session to. The service layer validates ownership before writing.
    """

    initial_query: Optional[Annotated[str, Field(min_length=1)]] = Field(
        None,
        description=(
            "Optional first message. If supplied, the session is created "
            "with a derived title and the message is persisted."
        ),
    )
    course_id: Optional[UUID] = Field(
        None,
        description=(
            "Optional course to attach the session to. Must be owned "
            "by the authenticated user."
        ),
    )
    document_id: Optional[UUID] = Field(
        None,
        description=(
            "Optional document to attach the session to. Must be owned "
            "by the authenticated user."
        ),
    )


class ChatSessionUpdate(BaseModel):
    """Partial update — typically renaming a session.

    Phase 6B: ``course_id`` accepts a UUID (assign), or ``null``
    (unlink). The service layer validates ownership before writing.
    """

    model_config = ConfigDict(extra="forbid")

    title: TitleStr | None = None
    course_id: Optional[UUID] = None


class ChatSessionResponse(ChatSessionBase):
    """Public chat session representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    # Phase 6B: nullable course link. ``null`` means "uncoursed".
    course_id: Optional[UUID] = None
    # Phase 6E: nullable document link. ``null`` means "undocumented".
    document_id: Optional[UUID] = None
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


class ChatMessageWithSourcesResponse(ChatMessageResponse):
    """A chat message plus its persisted citations."""

    sources: List["ChatMessageSourceResponse"] = Field(default_factory=list)


# ---------- ChatMessageSource ----------


class ChatMessageSourceResponse(BaseModel):
    """Public representation of a single citation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message_id: UUID
    document_id: UUID
    chunk_id: str
    position: int = Field(..., ge=1)
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    score: Optional[float] = None
    snippet: Optional[str] = None


# ---------- Session + history ----------


class ChatSessionWithMessagesResponse(ChatSessionResponse):
    """Session metadata plus the full ordered message history."""

    messages: List[ChatMessageWithSourcesResponse] = Field(default_factory=list)


# ---------- RAG Q&A (one-shot /chat endpoint) ----------


class ChatRequest(BaseModel):
    """Payload for the /chat endpoint."""

    query: Annotated[str, Field(min_length=1, description="The user's question.")]
    document_id: Optional[UUID] = Field(
        None,
        description=(
            "Optional document ID to restrict the answer to a single document. "
            "Must be owned by the authenticated user."
        ),
    )
    mode: Literal["semantic", "hybrid"] = Field(
        "semantic",
        description="Retrieval mode forwarded to the retrieval service.",
    )
    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum number of context chunks to retrieve.",
    )
    score_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Optional minimum dense similarity score.",
    )
    temperature: float = Field(
        0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature passed to the LLM.",
    )
    max_output_tokens: int = Field(
        1024,
        ge=1,
        le=8192,
        description="Maximum number of tokens the LLM may produce.",
    )

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query string cannot be empty or only whitespace.")
        return v.strip()


class ChatSource(BaseModel):
    """A single citation surfaced in a chat response."""

    index: int = Field(..., ge=1, description="1-based source index.")
    chunk_id: str
    document_id: Optional[UUID] = None
    document_title: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: int
    score: float
    snippet: str


class ChatResponse(BaseModel):
    """Response from the /chat endpoint."""

    answer: str
    sources: List[ChatSource]
    model: str
    retrieval_mode: Literal["semantic", "hybrid"]
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


# ---------- Session-based Q&A ----------


class SendMessageRequest(BaseModel):
    """Payload for sending a message into an existing chat session."""

    query: Annotated[str, Field(min_length=1, description="The user's question.")]
    document_id: Optional[UUID] = Field(
        None,
        description=(
            "Optional document ID to restrict the answer to a single document. "
            "Must be owned by the authenticated user."
        ),
    )
    mode: Literal["semantic", "hybrid"] = Field(
        "semantic",
        description="Retrieval mode forwarded to the retrieval service.",
    )
    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum number of context chunks to retrieve.",
    )
    score_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Optional minimum dense similarity score.",
    )
    temperature: float = Field(
        0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature passed to the LLM.",
    )
    max_output_tokens: int = Field(
        1024,
        ge=1,
        le=8192,
        description="Maximum number of tokens the LLM may produce.",
    )

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query string cannot be empty or only whitespace.")
        return v.strip()


class SendMessageResponse(BaseModel):
    """Response from the session message endpoint.

    Returns the persisted user message, the assistant reply, and the
    citations attached to the assistant message.
    """

    user_message: ChatMessageResponse
    assistant_message: ChatMessageWithSourcesResponse
    model: str
    retrieval_mode: Literal["semantic", "hybrid"]
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


# Rebuild models that reference forward-declared types so Pydantic
# resolves them at import time.
ChatMessageWithSourcesResponse.model_rebuild()
