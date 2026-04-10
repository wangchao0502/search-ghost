"""L1 Ingestion — FastAPI router for HTTP file upload."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi import File as FastAPIFile

from search_ghost.deps import KBDep
from search_ghost.models import DocumentMeta, DocumentStatus, IngestResponse, ProcessingTask

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("", response_model=IngestResponse)
async def ingest_file(
    kb: KBDep,
    file: UploadFile = FastAPIFile(...),
    title: str | None = None,
    tags: str = "",  # comma-separated
) -> IngestResponse:
    """Upload a file for ingestion. Returns task_id immediately (non-blocking)."""
    raw = await file.read()
    filename = file.filename or "untitled"
    content_type = file.content_type or _guess_mime(filename)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    meta = DocumentMeta(
        title=title or Path(filename).stem,
        source_url=None,
        content_type=content_type,
        tags=tag_list,
        status=DocumentStatus.PENDING,
    )

    # Persist raw file + meta
    await kb.document_store.save_meta(meta)
    await kb.document_store.save_raw(meta.doc_id, "original", raw)

    # Queue processing task
    task = ProcessingTask(doc_id=meta.doc_id)
    await kb.task_queue.enqueue(task)

    return IngestResponse(task_id=task.task_id, doc_id=meta.doc_id)


@router.post("/text", response_model=IngestResponse)
async def ingest_text(
    kb: KBDep,
    title: str = "Untitled",
    content: str = "",
    tags: str = "",
) -> IngestResponse:
    """Ingest raw text directly (no file upload needed)."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    meta = DocumentMeta(
        title=title,
        content_type="text/markdown",
        tags=tag_list,
        status=DocumentStatus.PENDING,
    )

    raw = content.encode("utf-8")
    await kb.document_store.save_meta(meta)
    await kb.document_store.save_raw(meta.doc_id, "original", raw)

    task = ProcessingTask(doc_id=meta.doc_id)
    await kb.task_queue.enqueue(task)

    return IngestResponse(task_id=task.task_id, doc_id=meta.doc_id)


def _guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "text/plain"
