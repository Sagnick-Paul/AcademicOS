"""Recursive Character Chunking service."""
from __future__ import annotations

import bisect
import time
from typing import List, Optional, Sequence, Tuple
from app.processing.schemas import Chunk

class ChunkingService:
    """Service to recursively split text into overlapping chunks.

    When ``page_metadata`` is supplied (a sequence of ``{"page_index", "text"}``
    records from an extractor), each produced :class:`Chunk` carries a
    ``page`` field in its ``metadata`` mapping identifying which source
    page the chunk's text came from. This is what the RAG layer uses
    to render citations back to the user.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        separators: Optional[List[str]] = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def chunk_text(
        self,
        text: str,
        page_metadata: Optional[Sequence[dict]] = None,
    ) -> Tuple[List[Chunk], float]:
        """Split text recursively and return Chunk objects with stats.

        Handles page-aware or flat text.
        Returns (list of chunks, duration in seconds).
        """
        start_time = time.perf_counter()

        # If text is empty, return empty list immediately
        if not text:
            return [], time.perf_counter() - start_time

        # Precompute page boundaries so we can attribute each chunk to a
        # source page. Boundaries are cumulative character offsets into
        # ``text``; the page index of any offset is the position of the
        # last boundary <= offset.
        page_offsets, page_numbers = self._build_page_index(text, page_metadata)

        # Simple recursive splitter implementation
        raw_chunks = self._split_text(text, self.separators)

        # Build Chunk objects
        chunks: List[Chunk] = []
        # Track cursor to avoid scanning from offset 0 every chunk — chunks
        # are emitted in the same order as the source text.
        cursor = 0
        for i, chunk_text_str in enumerate(raw_chunks):
            page_num = self._resolve_page(
                cursor + text[cursor:].find(chunk_text_str),
                page_offsets,
                page_numbers,
            )
            chunks.append(
                Chunk(
                    text=chunk_text_str,
                    index=i,
                    metadata={"page": page_num} if page_num is not None else {},
                )
            )
            cursor += len(chunk_text_str)

        duration = time.perf_counter() - start_time
        return chunks, duration

    @staticmethod
    def _build_page_index(
        text: str,
        page_metadata: Optional[Sequence[dict]],
    ) -> Tuple[List[int], List[Optional[int]]]:
        """Build parallel lists of cumulative offsets and page numbers.

        Returns two lists of equal length: ``page_offsets[k]`` is the
        character offset in ``text`` where page ``page_numbers[k]`` begins.
        The final entry covers the end of the text so binary search still
        yields a result for content past the last real page.
        """
        if not page_metadata:
            return [], []

        offsets: List[int] = [0]
        numbers: List[Optional[int]] = []
        running = 0
        for page in page_metadata:
            page_text = page.get("text", "") or ""
            # Extractors return either ``page_index`` (0-based) or omit it.
            page_idx = page.get("page_index")
            numbers.append(page_idx)
            running += len(page_text)
            # Account for the separator that joins pages in the concatenated
            # source text. The PDF/PPTX/TXT processors join pages with a
            # single newline.
            running += 1
            offsets.append(running)
        # Tail guard so out-of-range lookups still resolve.
        offsets.append(len(text))
        numbers.append(numbers[-1] if numbers else None)
        return offsets, numbers

    @staticmethod
    def _resolve_page(
        offset: int,
        page_offsets: Sequence[int],
        page_numbers: Sequence[Optional[int]],
    ) -> Optional[int]:
        """Resolve a character offset to its source page number (1-based)."""
        if not page_offsets:
            return None
        # ``bisect_right`` gives us the insertion point — the index of the
        # boundary strictly after the offset. The page number is the one
        # associated with the preceding boundary.
        idx = bisect.bisect_right(page_offsets, offset) - 1
        if idx < 0:
            return None
        raw = page_numbers[min(idx, len(page_numbers) - 1)]
        if raw is None:
            return None
        # Convert 0-based page_index to 1-based for human display.
        return raw + 1

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
