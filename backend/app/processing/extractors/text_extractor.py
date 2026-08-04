"""Plain text extractor."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import aiofiles

from app.processing.base import BaseExtractor
from app.processing.exceptions import ExtractionFailed

class TextExtractor(BaseExtractor):
    """Extracts raw text from .txt files using async I/O."""

    async def extract(self, file_path: Path) -> Dict[str, Any]:
        try:
            # Async read using aiofiles
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()
        except UnicodeDecodeError:
            try:
                # Fallback to Latin-1
                async with aiofiles.open(file_path, mode="r", encoding="latin-1") as f:
                    content = await f.read()
            except Exception as exc:
                raise ExtractionFailed(f"Failed to read text file with fallback encoding: {exc}") from exc
        except Exception as exc:
            raise ExtractionFailed(f"Failed to read text file: {exc}") from exc

        # Text files don't have page concepts, so we represent them as a single page
        return {
            "text": content,
            "metadata": {
                "title": file_path.stem,
                "author": None,
                "pages": 1,
            },
            "pages": [
                {
                    "page_index": 0,
                    "text": content,
                }
            ],
        }
