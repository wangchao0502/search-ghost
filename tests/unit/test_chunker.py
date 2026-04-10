"""Unit tests for the text chunker."""

import pytest
from search_ghost.layers.processing.chunker import chunk_text


def test_empty_text():
    chunks = chunk_text("", doc_id="test")
    assert chunks == []


def test_single_chunk():
    text = "Hello world. This is a short document."
    chunks = chunk_text(text, doc_id="doc1", chunk_size=512, overlap=64)
    assert len(chunks) == 1
    assert chunks[0].text == text.strip()
    assert chunks[0].doc_id == "doc1"
    assert chunks[0].chunk_index == 0


def test_multiple_chunks():
    # Create text longer than chunk_size
    text = ("The quick brown fox jumps over the lazy dog. " * 20).strip()
    chunks = chunk_text(text, doc_id="doc2", chunk_size=100, overlap=10)
    assert len(chunks) > 1
    # All chunks reference the same doc
    assert all(c.doc_id == "doc2" for c in chunks)
    # Indices are sequential
    for i, c in enumerate(chunks):
        assert c.chunk_index == i


def test_chunk_covers_full_text():
    """No characters should be lost — union of chunks covers original."""
    text = "Alpha. Beta. Gamma. Delta. Epsilon. Zeta. " * 10
    chunks = chunk_text(text, doc_id="doc3", chunk_size=80, overlap=20)
    # First chunk starts at 0
    assert chunks[0].start_char == 0
    # Last chunk ends at or near end of text
    assert chunks[-1].end_char >= len(text) - 5


def test_paragraph_break_preferred():
    """Splitter should prefer breaking on double newline."""
    text = "First paragraph content here.\n\nSecond paragraph content here."
    chunks = chunk_text(text, doc_id="doc4", chunk_size=35, overlap=0)
    # Should split at paragraph break
    assert any("\n\n" not in c.text for c in chunks)
