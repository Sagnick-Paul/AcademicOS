"""Dispatcher mapping document type to correct processor."""
from __future__ import annotations

from pathlib import Path
from app.processing.factory import ProcessorFactory
from app.processing.schemas import ProcessingResult

class DocumentDispatcher:
    """Dispatches processing requests to the appropriate processor."""

    def __init__(self, factory: ProcessorFactory | None = None) -> None:
        self.factory = factory or ProcessorFactory()

    async def dispatch(
        self,
        file_path: Path,
        file_type: str,
        filename: str,
        file_size: int,
    ) -> ProcessingResult:
        """Resolve the processor and run the processing pipeline."""
        processor = self.factory.get_processor(file_type)
        return await processor.process(file_path, filename=filename, file_size=file_size)
