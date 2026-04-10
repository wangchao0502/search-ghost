"""Search API router."""

from __future__ import annotations

from fastapi import APIRouter, Query

from search_ghost.deps import KBDep
from search_ghost.layers.retrieval.hybrid_search import hybrid_search
from search_ghost.models import QueryMode, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    kb: KBDep,
    q: str = Query(..., description="Search query"),
    top_k: int = Query(6, ge=1, le=50),
    mode: QueryMode = Query(QueryMode.HYBRID),
) -> SearchResponse:
    if mode == QueryMode.HYBRID or mode == QueryMode.VECTOR:
        results = await hybrid_search(q, kb, top_k=top_k)
    else:
        results = await kb.vector_store.bm25_search(q, top_k=top_k)
        for r in results:
            meta = await kb.document_store.get_meta(r.doc_id)
            if meta:
                r.doc_title = meta.title

    return SearchResponse(query=q, results=results, total=len(results))
