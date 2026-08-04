"""Recursive Character Chunking service."""
from __future__ import annotations

import time
from typing import List, Optional
from app.processing.schemas import Chunk

class ChunkingService:
    """Service to recursively split text into overlapping chunks."""

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        separators: Optional[List[str]] = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def chunk_text(self, text: str, page_metadata: Optional[List[dict]] = None) -> tuple[List[Chunk], float]:
        """Split text recursively and return Chunk objects with stats.

        Handles page-aware or flat text.
        Returns (list of chunks, duration in seconds).
        """
        start_time = time.perf_counter()
        
        # If text is empty, return empty list immediately
        if not text:
            return [], time.perf_counter() - start_time

        # Simple recursive splitter implementation
        raw_chunks = self._split_text(text, self.separators)
        
        # Build Chunk objects
        chunks = []
        for i, chunk_text in enumerate(raw_chunks):
            # Try to associate chunks with page metadata if available
            metadata = {}
            if page_metadata:
                # Find which page(s) this chunk's text belongs to
                # For this step, if page_metadata is provided, we can estimate
                # or attach relevant context. We'll pass it along or keep it simple.
                pass
            chunks.append(Chunk(text=chunk_text, index=i, metadata=metadata))

        duration = time.perf_counter() - start_time
        return chunks, duration

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text by separators until chunks fit chunk_size."""
        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            # Fallback to hard character-based split if no separators left
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.overlap)]

        separator = separators[0]
        next_separators = separators[1:]

        # Split text by current separator
        if separator == "":
            splits = list(text)
        else:
            splits = text.split(separator)

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for split in splits:
            split_len = len(split)
            # If the single split exceeds chunk_size, recursively split it using next separators
            if split_len > self.chunk_size:
                # Flush current chunk first
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                    current_chunk = []
                    current_len = 0
                
                # Recursively split the oversized part
                sub_chunks = self._split_text(split, next_separators)
                chunks.extend(sub_chunks)
                continue

            # Check if adding this split exceeds chunk_size
            join_len = len(separator) if current_chunk else 0
            if current_len + join_len + split_len > self.chunk_size:
                # Flush
                chunks.append(separator.join(current_chunk))
                
                # Handle overlap: keep previous items that fit overlap budget
                overlap_chunk: List[str] = []
                overlap_len = 0
                for prev in reversed(current_chunk):
                    prev_join_len = len(separator) if overlap_chunk else 0
                    if overlap_len + prev_join_len + len(prev) <= self.overlap:
                        overlap_chunk.insert(0, prev)
                        overlap_len += prev_join_len + len(prev)
                    else:
                        break
                
                current_chunk = overlap_chunk
                current_len = overlap_len

            current_chunk.append(split)
            current_len += (len(separator) if len(current_chunk) > 1 else 0) + split_len

        if current_chunk:
            chunks.append(separator.join(current_chunk))

        # Filter out empty chunks and strip them
        return [c.strip() for c in chunks if c.strip()]
