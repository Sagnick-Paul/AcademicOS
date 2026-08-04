"""Pipeline orchestrator for document processing."""
from __future__ import annotations

from pathlib import Path
from app.processing.dispatcher import DocumentDispatcher
from app.processing.schemas import ProcessingResult
from app.processing.exceptions import ProcessingFailed, ProcessingError

class DocumentProcessingPipeline:
    """Coordinating pipeline for document processing runs."""

    def __init__(self, dispatcher: DocumentDispatcher | None = None) -> None:
        self.dispatcher = dispatcher or DocumentDispatcher()

    async def run(
        self,
        file_path: Path,
        file_type: str,
        filename: str,
        file_size: int,
    ) -> ProcessingResult:
        """Execute the document processing pipeline on the target file.

        Raises ProcessingFailed if any processing error occurs.
        """
        try:
            return await self.dispatcher.dispatch(
                file_path=file_path,
                file_type=file_type,
                filename=filename,
                file_size=file_size,
            )
        except ProcessingError as exc:
            # Re-raise known domain exceptions
            raise exc
        except Exception as exc:
            # Wrap unexpected exceptions
            raise ProcessingFailed(f"An unexpected error occurred during processing: {exc}") from exc
