"""
Recursive character text splitter.
Splits on paragraph → sentence → word boundaries to respect chunk_size.
"""

from __future__ import annotations

import re

from search_ghost.models import Chunk


_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _split_text(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int]]:
    """Return list of (start, end) char indices."""
    spans: list[tuple[int, int]] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        # Try to find a clean break point
        if end < length:
            for sep in _SEPARATORS[:-1]:
                idx = text.rfind(sep, start, end)
                if idx != -1 and idx > start:
                    end = idx + len(sep)
                    break
        spans.append((start, end))
        next_start = end - overlap
        start = next_start if next_start > start else end
    return spans


def chunk_text(
    text: str,
    doc_id: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    spans = _split_text(text, chunk_size, overlap)
    chunks: list[Chunk] = []
    for idx, (start, end) in enumerate(spans):
        piece = text[start:end].strip()
        if not piece:
            continue
        chunks.append(
            Chunk(
                doc_id=doc_id,
                text=piece,
                chunk_index=idx,
                start_char=start,
                end_char=end,
            )
        )
    return chunks
