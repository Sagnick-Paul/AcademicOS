"""PDF processor coordinating text and metadata extraction."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

from app.processing.base import BaseProcessor
from app.processing.extractors.pymupdf_extractor import PyMuPDFExtractor
from app.processing.cleaners import clean_text
from app.processing.chunking import ChunkingService
from app.processing.schemas import ProcessingResult, DocumentMetadata, ProcessingStats

class PDFTextExtractor:
    """Sub-component responsible for extracting raw text from PDF."""
    def __init__(self, extractor: PyMuPDFExtractor) -> None:
        self.extractor = extractor

    async def extract_text(self, file_path: Path) -> tuple[str, list[dict[str, Any]]]:
        result = await self.extractor.extract(file_path)
        return result["text"], result["pages"]

class PDFMetadataExtractor:
    """Sub-component responsible for extracting PDF metadata."""
    def __init__(self, extractor: PyMuPDFExtractor) -> None:
        self.extractor = extractor

    async def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        result = await self.extractor.extract(file_path)
        return result["metadata"]

class PDFProcessor(BaseProcessor):
    """Coordinates PDF extraction, cleaning, and chunking."""

    def __init__(
        self,
        extractor: PyMuPDFExtractor | None = None,
        chunking_service: ChunkingService | None = None,
    ) -> None:
        self.raw_extractor = extractor or PyMuPDFExtractor()
        self.text_extractor = PDFTextExtractor(self.raw_extractor)
        self.metadata_extractor = PDFMetadataExtractor(self.raw_extractor)
        self.chunker = chunking_service or ChunkingService()

    async def process(self, file_path: Path, filename: str, file_size: int) -> ProcessingResult:
        start_time = time.perf_counter()
        
        # 1. Extraction (delegated to sub-components)
        raw_text, pages = await self.text_extractor.extract_text(file_path)
        raw_meta = await self.metadata_extractor.extract_metadata(file_path)

        # 2. Cleaning
        cleaned_text, cleaning_time = clean_text(raw_text)

        # 3. Chunking
        chunks, chunking_time = self.chunker.chunk_text(cleaned_text, page_metadata=pages)

        # 4. Processing Stats
        words = len(cleaned_text.split())
        chars = len(cleaned_text)
        
        stats = ProcessingStats(
            pages=raw_meta.get("pages", 1),
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
            pages=raw_meta.get("pages", 1),
            words=words,
            characters=chars,
            language=None, # TBD in future
            document_type="pdf",
            title=raw_meta.get("title") or filename,
            author=raw_meta.get("author"),
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
