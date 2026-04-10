"""
Document CRUD using the ObjectStore.

Layout per document:
  documents/{doc_id}/meta.json       — DocumentMeta
  documents/{doc_id}/content.md      — processed text
  documents/{doc_id}/raw/            — original uploaded file(s)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from functools import partial

from search_ghost.layers.storage.object_store import ObjectStore
from search_ghost.models import Document, DocumentMeta, DocumentStatus


class DocumentStore:
    def __init__(self, store: ObjectStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _meta_rel(self, doc_id: str) -> str:
        return f"documents/{doc_id}/meta.json"

    def _content_rel(self, doc_id: str) -> str:
        return f"documents/{doc_id}/content.md"

    def _raw_rel(self, doc_id: str, filename: str) -> str:
        return f"documents/{doc_id}/raw/{filename}"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def save_meta(self, meta: DocumentMeta) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(self._store.write_json, self._meta_rel(meta.doc_id), meta.model_dump(mode="json")),
        )

    async def get_meta(self, doc_id: str) -> DocumentMeta | None:
        rel = self._meta_rel(doc_id)
        loop = asyncio.get_event_loop()
        exists = await loop.run_in_executor(None, self._store.exists, rel)
        if not exists:
            return None
        data = await loop.run_in_executor(None, self._store.read_json, rel)
        return DocumentMeta.model_validate(data)

    async def save_content(self, doc_id: str, content: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(self._store.write_text, self._content_rel(doc_id), content),
        )

    async def get_content(self, doc_id: str) -> str | None:
        rel = self._content_rel(doc_id)
        loop = asyncio.get_event_loop()
        exists = await loop.run_in_executor(None, self._store.exists, rel)
        if not exists:
            return None
        return await loop.run_in_executor(None, self._store.read_text, rel)

    async def save_raw(self, doc_id: str, filename: str, data: bytes) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(self._store.write_bytes, self._raw_rel(doc_id, filename), data),
        )

    async def get_document(self, doc_id: str) -> Document | None:
        meta = await self.get_meta(doc_id)
        if meta is None:
            return None
        content = await self.get_content(doc_id) or ""
        return Document(meta=meta, content=content)

    async def list_documents(self) -> list[DocumentMeta]:
        loop = asyncio.get_event_loop()
        entries = await loop.run_in_executor(None, self._store.ls, "documents")
        metas: list[DocumentMeta] = []
        for entry in entries:
            doc_id = entry.rstrip("/").split("/")[-1]
            meta = await self.get_meta(doc_id)
            if meta:
                metas.append(meta)
        return sorted(metas, key=lambda m: m.created_at, reverse=True)

    async def update_status(self, doc_id: str, status: DocumentStatus, **kwargs: object) -> None:
        meta = await self.get_meta(doc_id)
        if meta is None:
            return
        meta.status = status
        meta.updated_at = datetime.utcnow()
        for k, v in kwargs.items():
            setattr(meta, k, v)
        await self.save_meta(meta)

    async def delete(self, doc_id: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(self._store.rm, f"documents/{doc_id}", True),
        )
