"""Chat API router — SSE streaming RAG."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from search_ghost.deps import KBDep
from search_ghost.layers.generation.rag_pipeline import rag_stream
from search_ghost.models import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(kb: KBDep, req: ChatRequest) -> StreamingResponse:
    """Stream RAG response as Server-Sent Events."""
    return StreamingResponse(
        rag_stream(req.messages, kb, query_mode=req.query_mode, top_k=req.top_k),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
