"""Document processors package."""
from __future__ import annotations

from app.processing.processors.pdf_processor import PDFProcessor
from app.processing.processors.ppt_processor import PPTProcessor
from app.processing.processors.text_processor import TextProcessor
from app.processing.processors.image_processor import ImageProcessor

__all__ = [
    "PDFProcessor",
    "PPTProcessor",
    "TextProcessor",
    "ImageProcessor",
]
