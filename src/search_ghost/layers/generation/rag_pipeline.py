"""
RAG pipeline: retrieve → assemble context → stream LLM → yield SSE chunks.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from search_ghost.kb import KnowledgeBase
from search_ghost.layers.generation.citation_builder import build_context, build_messages
from search_ghost.layers.generation.llm_client import stream_completion
from search_ghost.layers.retrieval.hybrid_search import hybrid_search
from search_ghost.models import ChatMessage, QueryMode, SearchResult

logger = logging.getLogger(__name__)


async def rag_stream(
    messages: list[ChatMessage],
    kb: KnowledgeBase,
    query_mode: QueryMode = QueryMode.HYBRID,
    top_k: int | None = None,
) -> AsyncIterator[str]:
    """
    Yields Server-Sent Event strings.
    Event types:
      data: {"type": "sources", "results": [...]}
      data: {"type": "delta",   "content": "..."}
      data: {"type": "done"}
    """
    settings = kb.settings
    k = top_k or settings.top_k

    # Use the last user message as the retrieval query
    query = ""
    for m in reversed(messages):
        if m.role == "user":
            query = m.content
            break

    # ── Retrieve ────────────────────────────────────────────────────────
    results: list[SearchResult] = []
    if query and query_mode != QueryMode.BM25:
        results = await hybrid_search(query, kb, top_k=k)
    elif query and query_mode == QueryMode.BM25:
        results = await kb.vector_store.bm25_search(query, top_k=k)

    # Send sources event
    sources_payload = [
        {
            "chunk_id": r.chunk_id,
            "doc_id": r.doc_id,
            "doc_title": r.doc_title,
            "text": r.text[:200],
            "score": round(r.score, 4),
        }
        for r in results
    ]
    yield f"data: {json.dumps({'type': 'sources', 'results': sources_payload})}\n\n"

    # ── Assemble context + messages ─────────────────────────────────────
    context = build_context(results)
    lm_messages = build_messages(
        [{"role": m.role, "content": m.content} for m in messages],
        context,
    )

    # ── Stream LLM ──────────────────────────────────────────────────────
    async for delta in stream_completion(
        lm_messages,
        model=settings.llm_model,
        api_base=settings.llm_api_base,
        api_key=settings.llm_api_key,
    ):
        yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"
