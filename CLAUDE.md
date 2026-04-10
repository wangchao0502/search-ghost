# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

**search-ghost** — local-first personal KB: multi-modal ingest, hybrid search + RAG chat, optional knowledge graph, web UI and CLI. KB is a portable folder; storage can be local or S3-compatible via fsspec.

## Commands

```bash
uv sync
uv run uvicorn search_ghost.main:app --reload --port 8000   # backend
cd web && pnpm install && pnpm dev                          # frontend; /api/* → :8000
cd web && pnpm build                                        # static/ for prod

uv run ghost --help
uv run ghost serve --kb-path ./my-kb
uv run ghost ingest <file|path> && uv run ghost ingest --batch ./folder/
uv run ghost search "query" && uv run ghost chat "question"

uv run pytest
uv run ruff check src/ && uv run ruff format src/ && uv run mypy src/search_ghost/
```

## Architecture

Layers under `src/search_ghost/layers/`; `KnowledgeBase` is wired through FastAPI `deps.py`.

`Ingestion → Processing → Storage → Retrieval → Generation → Output` (L1–L6)

| Layer | Role |
|-------|------|
| **L1 Ingestion** | Normalize to `IngestRequest`, enqueue `ProcessingTask`, return task id. Ext: `search_ghost.ingestors`. |
| **L2 Processing** | Bytes → text → chunks → embeddings. **direct_pipeline** (ThreadPoolExecutor, interactive); **daft_pipeline** + **udfs** (batch, `GHOST_DAFT_RUNNER=ray` optional). Parsers: `search_ghost.parsers`. |
| **L3 Storage** | KB root: `.ghost/config.json`, `task_queue.db`, `documents/{uuid}/`, `chunks/`, `index/vectors.lance/`, `index/graph/` (LightRAG). I/O via `object_store.py` + fsspec. |
| **L4 Retrieval** | `hybrid_search`: BM25 + vectors, RRF. `graph_traversal`: LightRAG `aquery`. Optional reranker. |
| **L5 Generation** | LiteLLM streaming; `rag_pipeline` + `citation_builder` (`[source: uuid]`). |
| **L6 Output** | `ExporterBase`; ext: `search_ghost.exporters`. |

**Constraints:** No Redis — `asyncio.Queue` + SQLite (`worker/queue.py`). Heavy work in **ThreadPoolExecutor** (not multiprocessing). **LanceDB** holds vectors + BM25; **LightRAG** keeps its own files under `index/graph/` — do not move that into LanceDB. Insert full doc text to LightRAG; Lance chunks stay separate for search. Dev: Vite proxies `/api/*`; prod: `ghost serve` serves `static/`.

## Stack (short)

Python 3.11+ · FastAPI · uv · Typer · LanceDB · LightRAG · Daft · Docling / PaddleOCR / faster-whisper · LiteLLM · React 19 · Vite · TanStack Query · Zustand.

## Phases

| # | Focus |
|---|--------|
| 1 | MVP: text search, RAG, KB + web Search/Ingest |
| 2 | Multi-modal + Daft batch + S3, Documents/Tasks UI |
| 3 | Graph: LightRAG + GraphPage |
| 4 | Plugins + exporters + Settings |

## Frontend (`web/src/`)

`pages/` · `components/{search,chat,graph}/` · `api/` · `hooks/` (`useSSE`, `useWebSocket`) · `stores/`.
