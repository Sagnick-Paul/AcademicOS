"""OCR engine abstraction and stubs."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

class OCREngine(ABC):
    """Abstract interface for OCR engines (e.g. PaddleOCR, Tesseract)."""

    @abstractmethod
    async def extract_text(self, image_path: Path) -> str:
        """Extract text from an image file."""
        pass

class StubOCREngine(OCREngine):
    """Default placeholder OCR engine for testing and local runs without deps."""

    async def extract_text(self, image_path: Path) -> str:
        """Simulate OCR extraction from image filename/metadata."""
        # Simple placeholder content to allow pipeline testing
        return f"[OCR Stub Text extracted from {image_path.name}]"
