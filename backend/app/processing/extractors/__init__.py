"""Document extractors."""
from __future__ import annotations

from app.processing.extractors.ocr import OCREngine, StubOCREngine
from app.processing.extractors.pymupdf_extractor import PyMuPDFExtractor
from app.processing.extractors.pptx_extractor import PPTXExtractor
from app.processing.extractors.text_extractor import TextExtractor

__all__ = [
    "OCREngine",
    "StubOCREngine",
    "PyMuPDFExtractor",
    "PPTXExtractor",
    "TextExtractor",
]
