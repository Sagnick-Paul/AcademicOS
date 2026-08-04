"""Factory to resolve document processors based on file type."""
from __future__ import annotations

from app.processing.base import BaseProcessor
from app.processing.exceptions import UnsupportedDocumentType
from app.processing.processors.pdf_processor import PDFProcessor
from app.processing.processors.ppt_processor import PPTProcessor
from app.processing.processors.text_processor import TextProcessor
from app.processing.processors.image_processor import ImageProcessor

class ProcessorFactory:
    """Factory yielding the appropriate BaseProcessor for a given file type."""

    @staticmethod
    def get_processor(file_type: str) -> BaseProcessor:
        """Resolve a processor by canonical file type.

        Raises UnsupportedDocumentType if the type is not recognized.
        """
        ft = file_type.lower().strip()
        if ft == "pdf":
            return PDFProcessor()
        elif ft in ("ppt", "pptx"):
            return PPTProcessor()
        elif ft == "txt":
            return TextProcessor()
        elif ft in ("png", "jpg", "jpeg"):
            return ImageProcessor()
        else:
            raise UnsupportedDocumentType(f"No processor registered for file type: {file_type}")
