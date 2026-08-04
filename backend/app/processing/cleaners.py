"""Text cleaning pipeline for document processing."""
from __future__ import annotations

import re
import unicodedata
import time

def normalize_unicode(text: str) -> str:
    """Normalize unicode to NFKC form."""
    return unicodedata.normalize("NFKC", text)

def strip_null_bytes(text: str) -> str:
    """Remove null bytes from text."""
    return text.replace("\x00", "")

def normalize_whitespace(text: str) -> str:
    """Replace tabs and various space characters with standard spaces."""
    # Replace tabs with 4 spaces
    text = text.replace("\t", "    ")
    # Replace carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text

def remove_excessive_newlines(text: str) -> str:
    """Reduce 3 or more consecutive newlines to exactly 2 newlines."""
    return re.sub(r"\n{3,}", "\n\n", text)

def clean_text(text: str) -> tuple[str, float]:
    """Apply the complete cleaning pipeline to the text.

    Returns the cleaned text and the cleaning duration in seconds.
    """
    start_time = time.perf_counter()
    if not text:
        return "", time.perf_counter() - start_time
    
    text = strip_null_bytes(text)
    text = normalize_unicode(text)
    text = normalize_whitespace(text)
    text = remove_excessive_newlines(text)
    text = text.strip()
    
    return text, time.perf_counter() - start_time
