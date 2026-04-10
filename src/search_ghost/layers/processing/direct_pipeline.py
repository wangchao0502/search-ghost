"""
Direct (single-doc) processing pipeline.
parse → chunk → embed → store (LanceDB + DocumentStore).
"""

from __future__ import annotations

import logging

from search_ghost.kb import KnowledgeBase
from search_ghost.layers.processing.chunker import chunk_text
from search_ghost.layers.processing.embedder import embed_chunks
from search_ghost.layers.processing.parsers.registry import get_parser
from search_ghost.models import DocumentStatus, ProcessingTask

logger = logging.getLogger(__name__)


class DirectPipeline:
    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    async def process(self, task: ProcessingTask) -> None:
        kb = self._kb
        doc_id = task.doc_id
        settings = kb.settings

        try:
            await kb.task_queue.update_progress(task.task_id, 5)

            # ── 1. Load raw file ────────────────────────────────────────────
            doc = await kb.document_store.get_document(doc_id)
            if doc is None:
                raise ValueError(f"Document {doc_id} not found")

            content_type = doc.meta.content_type
            raw_bytes: bytes | None = None

            # Try to load from raw/ first
            try:
                raw_bytes = kb.object_store.read_bytes(f"documents/{doc_id}/raw/original")
            except Exception:
                # Fall back: use content.md if already saved
                raw_bytes = doc.content.encode() if doc.content else None

            if not raw_bytes:
                raise ValueError("No raw content found")

            await kb.task_queue.update_progress(task.task_id, 20)

            # ── 2. Parse ────────────────────────────────────────────────────
            parser = get_parser(content_type)
            if parser is None:
                # Default: treat as plain text
                text = raw_bytes.decode("utf-8", errors="replace")
            else:
                text = parser.parse(raw_bytes, "original")

            await kb.document_store.save_content(doc_id, text)
            await kb.task_queue.update_progress(task.task_id, 40)

            # ── 3. Chunk ────────────────────────────────────────────────────
            chunks = chunk_text(
                text,
                doc_id=doc_id,
                chunk_size=settings.chunk_size,
                overlap=settings.chunk_overlap,
            )
            logger.debug("doc %s → %d chunks", doc_id, len(chunks))
            await kb.task_queue.update_progress(task.task_id, 60)

            # ── 4. Embed ────────────────────────────────────────────────────
            chunks = await embed_chunks(
                chunks,
                model=settings.embedding_model,
                api_base=settings.embedding_api_base,
                api_key=settings.embedding_api_key,
            )
            await kb.task_queue.update_progress(task.task_id, 80)

            # ── 5. Store in LanceDB ─────────────────────────────────────────
            await kb.vector_store.upsert_chunks(chunks)

            # Update document metadata
            await kb.document_store.update_status(
                doc_id,
                DocumentStatus.READY,
                chunk_count=len(chunks),
                char_count=len(text),
            )
            await kb.task_queue.update_progress(task.task_id, 100)
            await kb.task_queue.mark_completed(task.task_id)
            logger.info("Processed doc %s (%d chunks)", doc_id, len(chunks))

        except Exception as exc:
            logger.exception("Failed to process doc %s", doc_id)
            await kb.document_store.update_status(doc_id, DocumentStatus.FAILED)
            await kb.task_queue.mark_failed(task.task_id, str(exc))
