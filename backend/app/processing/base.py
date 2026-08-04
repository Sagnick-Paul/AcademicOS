"""Base interfaces for extractors and processors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

class BaseExtractor(ABC):
    """Abstract base class for extracting raw text and metadata from files."""

    @abstractmethod
    async def extract(self, file_path: Path) -> Dict[str, Any]:
        """Extract raw text and metadata.

        Returns a dictionary containing at least:
        - "text": str (concatenated raw text)
        - "metadata": dict (type-specific metadata fields)
        - "pages": list[dict] (page-by-page text and metadata)
        """
        pass

class BaseProcessor(ABC):
    """Abstract base class for coordinating document processing."""

    @abstractmethod
    async def process(self, file_path: Path, filename: str, file_size: int) -> Any:
        """Process the file end-to-end.

        Returns a ProcessingResult schema instance.
        """
        pass
