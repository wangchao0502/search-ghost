"""Unit tests for RRF fusion logic."""

from search_ghost.layers.retrieval.hybrid_search import _rrf_fuse
from search_ghost.models import SearchResult


def _make(chunk_id: str, score: float = 1.0) -> SearchResult:
    return SearchResult(chunk_id=chunk_id, doc_id="doc", text="text", score=score)


def test_rrf_no_overlap():
    v = [_make("a"), _make("b")]
    b = [_make("c"), _make("d")]
    fused = _rrf_fuse(v, b, k=60)
    # All 4 unique chunks should appear
    ids = [r.chunk_id for r in fused]
    assert set(ids) == {"a", "b", "c", "d"}


def test_rrf_overlap_boosted():
    """A chunk appearing in both lists should rank higher."""
    v = [_make("shared"), _make("only_vector")]
    b = [_make("shared"), _make("only_bm25")]
    fused = _rrf_fuse(v, b, k=60)
    top = fused[0]
    assert top.chunk_id == "shared"


def test_rrf_scores_positive():
    v = [_make("x")]
    b = [_make("x")]
    fused = _rrf_fuse(v, b, k=60)
    assert fused[0].score > 0
