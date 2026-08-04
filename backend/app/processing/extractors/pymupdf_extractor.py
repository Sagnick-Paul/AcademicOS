"""PDF extractor using PyMuPDF (fitz)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
# pyrefly: ignore [missing-import]
import fitz

from app.processing.base import BaseExtractor
from app.processing.exceptions import ExtractionFailed

class PyMuPDFExtractor(BaseExtractor):
    """Extracts text and metadata from PDF files using PyMuPDF."""

    async def extract(self, file_path: Path) -> Dict[str, Any]:
        try:
            # fitz operations are CPU-bound and synchronous.
            # We open the document directly.
            doc = fitz.open(file_path)
        except Exception as exc:
            raise ExtractionFailed(f"PyMuPDF failed to open file: {exc}") from exc

        try:
            pages = []
            full_text_list = []
            
            for i, page in enumerate(doc):
                page_text = page.get_text()
                full_text_list.append(page_text)
                pages.append({
                    "page_index": i,
                    "text": page_text,
                })

            full_text = "\n".join(full_text_list)
            meta = doc.metadata or {}

            result = {
                "text": full_text,
                "metadata": {
                    "title": meta.get("title") or file_path.stem,
                    "author": meta.get("author"),
                    "subject": meta.get("subject"),
                    "keywords": meta.get("keywords"),
                    "pages": len(doc),
                },
                "pages": pages,
            }
            doc.close()
            return result
        except Exception as exc:
            if 'doc' in locals():
                doc.close()
            raise ExtractionFailed(f"PyMuPDF failed during extraction: {exc}") from exc
