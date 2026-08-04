"""Intelligent Document Processing package."""
from __future__ import annotations

from app.processing.exceptions import (
    ProcessingError,
    UnsupportedDocumentType,
    ExtractionFailed,
    OCRFailed,
    ChunkingFailed,
    ProcessingFailed,
)
from app.processing.schemas import (
    Chunk,
    DocumentMetadata,
    ProcessingStats,
    ProcessingResult,
)
from app.processing.cleaners import clean_text
from app.processing.chunking import ChunkingService
from app.processing.dispatcher import DocumentDispatcher
from app.processing.factory import ProcessorFactory
from app.processing.pipeline import DocumentProcessingPipeline

__all__ = [
    "ProcessingError",
    "UnsupportedDocumentType",
    "ExtractionFailed",
    "OCRFailed",
    "ChunkingFailed",
    "ProcessingFailed",
    "Chunk",
    "DocumentMetadata",
    "ProcessingStats",
    "ProcessingResult",
    "clean_text",
    "ChunkingService",
    "DocumentDispatcher",
    "ProcessorFactory",
    "DocumentProcessingPipeline",
]
