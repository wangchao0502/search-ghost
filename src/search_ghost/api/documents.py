"""Documents API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from search_ghost.deps import KBDep
from search_ghost.models import Document, DocumentMeta

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentMeta])
async def list_documents(kb: KBDep) -> list[DocumentMeta]:
    return await kb.document_store.list_documents()


@router.get("/{doc_id}", response_model=Document)
async def get_document(doc_id: str, kb: KBDep) -> Document:
    doc = await kb.document_store.get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, kb: KBDep) -> dict:
    doc = await kb.document_store.get_meta(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await kb.document_store.delete(doc_id)
    await kb.vector_store.delete_by_doc(doc_id)
    return {"status": "deleted", "doc_id": doc_id}
