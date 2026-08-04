"""Image processor coordinating OCR, cleaning, and chunking."""
from __future__ import annotations

import time
from pathlib import Path

from app.processing.base import BaseProcessor
from app.processing.extractors.ocr import OCREngine, StubOCREngine
from app.processing.cleaners import clean_text
from app.processing.chunking import ChunkingService
from app.processing.schemas import ProcessingResult, DocumentMetadata, ProcessingStats

class ImageProcessor(BaseProcessor):
    """Coordinates OCR, cleaning, and chunking for images."""

    def __init__(
        self,
        ocr_engine: OCREngine | None = None,
        chunking_service: ChunkingService | None = None,
    ) -> None:
        self.ocr_engine = ocr_engine or StubOCREngine()
        self.chunker = chunking_service or ChunkingService()

    async def process(self, file_path: Path, filename: str, file_size: int) -> ProcessingResult:
        start_time = time.perf_counter()
        
        # 1. OCR Extraction
        raw_text = await self.ocr_engine.extract_text(file_path)

        # 2. Cleaning
        cleaned_text, cleaning_time = clean_text(raw_text)

        # 3. Chunking
        chunks, chunking_time = self.chunker.chunk_text(cleaned_text)

        # 4. Processing Stats
        words = len(cleaned_text.split())
        chars = len(cleaned_text)
        
        stats = ProcessingStats(
            pages=1,
            words=words,
            characters=chars,
            chunks_created=len(chunks),
            processing_time=time.perf_counter() - start_time,
            ocr_used=True,
            cleaning_time=cleaning_time,
            chunking_time=chunking_time,
        )

        # 5. Metadata Schema
        ext = file_path.suffix.lower().lstrip(".")
        meta = DocumentMetadata(
            filename=filename,
            file_size=file_size,
            pages=1,
            words=words,
            characters=chars,
            language=None,
            document_type=ext if ext in ("png", "jpg", "jpeg") else "png",
            title=filename,
            author=None,
            created_at=None,
            modified_at=None,
        )

        return ProcessingResult(
            cleaned_text=cleaned_text,
            chunks=chunks,
            metadata=meta,
            stats=stats,
            warnings=[],
        )
