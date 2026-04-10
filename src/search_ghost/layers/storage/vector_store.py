"""
LanceDB vector + BM25 FTS store.

Table schema (Arrow):
  chunk_id   string
  doc_id     string
  text       string  (BM25 full-text indexed)
  chunk_index int32
  start_char  int32
  end_char    int32
  vector      fixed_size_list<float32>[dim]
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING, Any

import lancedb
import pyarrow as pa

from search_ghost.models import Chunk, SearchResult

if TYPE_CHECKING:
    from lancedb.table import Table


TABLE_NAME = "chunks"


def _make_schema(dim: int) -> pa.Schema:
    return pa.schema(
        [
            pa.field("chunk_id", pa.string()),
            pa.field("doc_id", pa.string()),
            pa.field("text", pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("start_char", pa.int32()),
            pa.field("end_char", pa.int32()),
            pa.field("vector", pa.list_(pa.float32(), dim)),
        ]
    )


class VectorStore:
    def __init__(self, lance_path: str, dim: int = 1536) -> None:
        self._path = lance_path
        self._dim = dim
        self._db: lancedb.DBConnection | None = None
        self._table: Table | None = None

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _get_db(self) -> lancedb.DBConnection:
        if self._db is None:
            self._db = lancedb.connect(self._path)
        return self._db

    def _get_table(self) -> Table:
        if self._table is None:
            db = self._get_db()
            names = db.table_names()
            if TABLE_NAME in names:
                self._table = db.open_table(TABLE_NAME)
            else:
                schema = _make_schema(self._dim)
                self._table = db.create_table(TABLE_NAME, schema=schema)
                # Create FTS index on text column for BM25
                self._table.create_fts_index("text", replace=True)
        return self._table

    async def initialize(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._get_table)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def _chunks_to_records(self, chunks: list[Chunk]) -> list[dict[str, Any]]:
        records = []
        for c in chunks:
            records.append(
                {
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "text": c.text,
                    "chunk_index": c.chunk_index,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                    "vector": c.embedding or ([0.0] * self._dim),
                }
            )
        return records

    async def upsert_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        records = self._chunks_to_records(chunks)
        loop = asyncio.get_event_loop()

        def _write() -> None:
            tbl = self._get_table()
            # Delete old chunks for these doc_ids first
            doc_ids = list({c.doc_id for c in chunks})
            for doc_id in doc_ids:
                try:
                    tbl.delete(f"doc_id = '{doc_id}'")
                except Exception:
                    pass
            tbl.add(records)
            # Refresh FTS index
            tbl.create_fts_index("text", replace=True)

        await loop.run_in_executor(None, _write)

    async def delete_by_doc(self, doc_id: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._get_table().delete(f"doc_id = '{doc_id}'"))

    # ------------------------------------------------------------------
    # Read — vector search
    # ------------------------------------------------------------------

    async def vector_search(self, embedding: list[float], top_k: int = 10) -> list[SearchResult]:
        loop = asyncio.get_event_loop()

        def _search() -> list[dict[str, Any]]:
            tbl = self._get_table()
            return (
                tbl.search(embedding)
                .limit(top_k)
                .select(["chunk_id", "doc_id", "text", "chunk_index", "_distance"])
                .to_list()
            )

        rows = await loop.run_in_executor(None, _search)
        results = []
        for i, row in enumerate(rows):
            # Convert distance to score (lower distance = higher score)
            score = 1.0 / (1.0 + row.get("_distance", i + 1))
            results.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    doc_id=row["doc_id"],
                    text=row["text"],
                    score=score,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Read — BM25 / FTS search
    # ------------------------------------------------------------------

    async def bm25_search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        loop = asyncio.get_event_loop()

        def _search() -> list[dict[str, Any]]:
            tbl = self._get_table()
            return (
                tbl.search(query, query_type="fts")
                .limit(top_k)
                .select(["chunk_id", "doc_id", "text", "chunk_index", "_score"])
                .to_list()
            )

        try:
            rows = await loop.run_in_executor(None, _search)
        except Exception:
            return []

        results = []
        for i, row in enumerate(rows):
            score = row.get("_score", 1.0 / (i + 1))
            results.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    doc_id=row["doc_id"],
                    text=row["text"],
                    score=float(score),
                )
            )
        return results
