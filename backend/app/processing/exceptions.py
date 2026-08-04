"""Domain exceptions raised by the processing layer."""
from __future__ import annotations

class ProcessingError(Exception):
    """Base exception for all document processing errors."""
    pass

class UnsupportedDocumentType(ProcessingError):
    """Raised when a document type is not supported by any processor."""
    pass

class ExtractionFailed(ProcessingError):
    """Raised when raw content extraction fails."""
    pass

class OCRFailed(ProcessingError):
    """Raised when OCR extraction fails."""
    pass

class ChunkingFailed(ProcessingError):
    """Raised when text chunking fails."""
    pass

class ProcessingFailed(ProcessingError):
    """Raised when the document processing pipeline fails overall."""
    pass
