"""Pydantic schemas for document processing results and metadata."""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field

class Chunk(BaseModel):
    """A single text chunk extracted from a document."""
    text: str
    index: int
    metadata: dict[str, Any] = Field(default_factory=dict)

class DocumentMetadata(BaseModel):
    """Unified metadata extracted from a document."""
    filename: str
    file_size: int
    pages: Optional[int] = None
    words: Optional[int] = None
    characters: Optional[int] = None
    language: Optional[str] = None
    document_type: str  # pdf, ppt, pptx, png, jpg, jpeg, txt
    title: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

class ProcessingStats(BaseModel):
    """Detailed statistics about the document processing run."""
    pages: int = 0
    words: int = 0
    characters: int = 0
    chunks_created: int = 0
    processing_time: float = 0.0
    ocr_used: bool = False
    cleaning_time: float = 0.0
    chunking_time: float = 0.0

class ProcessingResult(BaseModel):
    """Unified result containing parsed content, chunks, metadata, and stats."""
    cleaned_text: str
    chunks: List[Chunk]
    metadata: DocumentMetadata
    stats: ProcessingStats
    warnings: List[str] = Field(default_factory=list)
