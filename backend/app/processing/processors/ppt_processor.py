"""PPTX processor coordinating PPTX slide/notes extraction, cleaning, and chunking."""
from __future__ import annotations

import time
from pathlib import Path

from app.processing.base import BaseProcessor
from app.processing.extractors.pptx_extractor import PPTXExtractor
from app.processing.cleaners import clean_text
from app.processing.chunking import ChunkingService
from app.processing.schemas import ProcessingResult, DocumentMetadata, ProcessingStats

class PPTProcessor(BaseProcessor):
    """Coordinates PPTX extraction, cleaning, and chunking."""

    def __init__(
        self,
        extractor: PPTXExtractor | None = None,
        chunking_service: ChunkingService | None = None,
    ) -> None:
        self.extractor = extractor or PPTXExtractor()
        self.chunker = chunking_service or ChunkingService()

    async def process(self, file_path: Path, filename: str, file_size: int) -> ProcessingResult:
        start_time = time.perf_counter()
        
        # 1. Extraction
        raw = await self.extractor.extract(file_path)

        # 2. Cleaning
        cleaned_text, cleaning_time = clean_text(raw["text"])

        # 3. Chunking
        chunks, chunking_time = self.chunker.chunk_text(cleaned_text, page_metadata=raw["pages"])

        # 4. Processing Stats
        words = len(cleaned_text.split())
        chars = len(cleaned_text)
        
        stats = ProcessingStats(
            pages=raw["metadata"].get("pages", 1),
            words=words,
            characters=chars,
            chunks_created=len(chunks),
            processing_time=time.perf_counter() - start_time,
            ocr_used=False,
            cleaning_time=cleaning_time,
            chunking_time=chunking_time,
        )

        # 5. Metadata Schema
        meta = DocumentMetadata(
            filename=filename,
            file_size=file_size,
            pages=raw["metadata"].get("pages", 1),
            words=words,
            characters=chars,
            language=None,
            document_type="pptx" if filename.lower().endswith("pptx") else "ppt",
            title=raw["metadata"].get("title") or filename,
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
