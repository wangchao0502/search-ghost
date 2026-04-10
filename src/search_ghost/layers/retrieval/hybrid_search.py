"""
Hybrid search: BM25 + vector in parallel, fused with Reciprocal Rank Fusion (RRF).
"""

from __future__ import annotations

import asyncio
import logging

from search_ghost.kb import KnowledgeBase
from search_ghost.layers.processing.embedder import embed_texts
from search_ghost.models import SearchResult

logger = logging.getLogger(__name__)


def _rrf_fuse(
    vector_results: list[SearchResult],
    bm25_results: list[SearchResult],
    k: int = 60,
) -> list[SearchResult]:
    """Reciprocal Rank Fusion of two ranked lists."""
    scores: dict[str, float] = {}
    data: dict[str, SearchResult] = {}

    for rank, result in enumerate(vector_results):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + 1.0 / (k + rank + 1)
        data[result.chunk_id] = result

    for rank, result in enumerate(bm25_results):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + 1.0 / (k + rank + 1)
        data[result.chunk_id] = result

    merged = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    fused: list[SearchResult] = []
    for cid in merged:
        r = data[cid].model_copy()
        r.score = scores[cid]
        fused.append(r)
    return fused


async def hybrid_search(
    query: str,
    kb: KnowledgeBase,
    top_k: int | None = None,
) -> list[SearchResult]:
    settings = kb.settings
    k = top_k or settings.top_k

    # Embed query
    embeddings = await embed_texts(
        [query],
        model=settings.embedding_model,
        api_base=settings.embedding_api_base,
        api_key=settings.embedding_api_key,
    )
    query_embedding = embeddings[0]

    # Run BM25 and vector search in parallel
    vector_task = kb.vector_store.vector_search(query_embedding, top_k=k * 2)
    bm25_task = kb.vector_store.bm25_search(query, top_k=k * 2)

    vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)

    logger.debug("vector=%d bm25=%d results before fusion", len(vector_results), len(bm25_results))

    fused = _rrf_fuse(vector_results, bm25_results, k=settings.rrf_k)

    # Annotate with document titles
    for result in fused[:k]:
        meta = await kb.document_store.get_meta(result.doc_id)
        if meta:
            result.doc_title = meta.title
            result.source_url = meta.source_url

    return fused[:k]
