# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**search-ghost** — local-first personal knowledge base supporting multi-modal data (text, PDF/Office, images, audio/video), knowledge graph, hybrid search, LLM-powered RAG chat, web UI, and CLI. Portable file-based storage works locally or on S3-compatible object storage. Production-quality, intended for open-source release.

---

## Development Commands

```bash
# Install dependencies
uv sync

# Start backend (dev, auto-reload)
uv run uvicorn search_ghost.main:app --reload --port 8000

# Start frontend (dev, Vite)
cd web && pnpm install && pnpm dev       # proxies /api/* to :8000

# CLI
uv run ghost --help
uv run ghost serve --kb-path ./my-kb
uv run ghost ingest ./file.pdf
uv run ghost ingest --batch ./folder/   # uses Daft batch path
uv run ghost search "query"
uv run ghost chat "question"

# Tests
uv run pytest                           # all tests
uv run pytest tests/unit/test_chunker.py          # single file
uv run pytest -k test_hybrid_search               # by name

# Lint / format / typecheck
uv run ruff check src/
uv run ruff format src/
uv run mypy src/search_ghost/

# Frontend build (outputs to static/ for prod serving)
cd web && pnpm build
```

---

## Architecture: Six Layers

All layers live under `src/search_ghost/layers/`. They communicate through the `KnowledgeBase` root object, injected via FastAPI's dependency system from `deps.py`.

```
Ingestion → Processing → Storage → Retrieval → Generation → Output
   (L1)         (L2)       (L3)       (L4)         (L5)       (L6)
```

### L1 — Ingestion (`layers/ingestion/`)
Accepts data from any source and normalizes it to `IngestRequest`. Puts a `ProcessingTask` on the queue and returns a task ID immediately (non-blocking). Connectors: HTTP upload, URL fetch, file watcher (`watchfiles`), clipboard paste. Extension point: `@register("name")` on an `IngestorBase` subclass, or declare via `pyproject.toml` entry_points `search_ghost.ingestors`.

### L2 — Processing (`layers/processing/`)
Transforms raw bytes → parsed text → chunks → embeddings → entity candidates.

Two execution paths share a unified `ProcessingPipeline` API (`process_one` / `process_batch`):
- **`direct_pipeline.py`** — single-doc async path using `ThreadPoolExecutor`. Used for interactive ingest. Keeps Docling/PaddleOCR/Whisper models alive in thread-local state.
- **`daft_pipeline.py`** — Daft DataFrame batch path. Used when `len(tasks) >= BATCH_THRESHOLD` (default 8) or `ghost ingest --batch`. Stateful UDFs in `udfs.py` load heavy models **once per partition**. Switch to Ray with `GHOST_DAFT_RUNNER=ray` in config — zero code change.

```python
# udfs.py pattern
@daft.udf(return_dtype=daft.DataType.python())
class ParseUDF:
    def __init__(self):
        self._registry = get_parser_registry()  # Docling/PaddleOCR/Whisper loaded ONCE
    def __call__(self, paths, content_types): ...
```

Parsers are MIME-type keyed (`registry.py`). Extension point: `search_ghost.parsers` entry_points.

### L3 — Storage (`layers/storage/`)
Portable KB file format — a self-contained folder, copyable anywhere:

```
{kb-root}/
├── .ghost/config.json          # name, schema_version, settings
├── .ghost/task_queue.db        # SQLite task persistence (survives restart)
├── documents/{uuid}/
│   ├── meta.json               # title, source_url, tags, content_type, status
│   ├── content.md              # canonical processed text
│   └── raw/                    # original file (original.pdf, etc.)
├── chunks/{uuid}.jsonl         # pre-computed chunks with metadata
├── index/vectors.lance/        # LanceDB: vector + BM25 FTS (Arrow IPC, S3-compatible)
└── index/graph/                # LightRAG working_dir: entities, relations, kv_store JSON
```

`object_store.py` uses `fsspec` — all file I/O goes through it. Local `file://` or S3 `s3://` is a one-line config change. LanceDB also supports fsspec natively.

### L4 — Retrieval (`layers/retrieval/`)
`hybrid_search.py` runs BM25 and vector search in parallel via `asyncio.gather`, fuses with Reciprocal Rank Fusion (RRF). No separate FTS engine — LanceDB's built-in Tantivy BM25 covers it.

`graph_traversal.py` wraps `LightRAG.aquery(mode="hybrid")` for entity-aware multi-hop retrieval. Query modes: `naive`, `local`, `global`, `hybrid`.

Optional `reranker.py` (cross-encoder) improves top-N quality.

### L5 — Generation (`layers/generation/`)
`llm_client.py` wraps `litellm.acompletion(stream=True)`. Provider is purely config-driven:
- `"openai/gpt-4o"`, `"anthropic/claude-opus-4-6"`, `"deepseek/deepseek-chat"`, `"gemini/gemini-2.5-pro"`, `"ollama/llama3.1"` — zero code change to add new providers.

`rag_pipeline.py`: retrieve → assemble context → stream LLM → yield SSE chunks.
`citation_builder.py`: tracks chunk IDs in context → appends `[source: uuid]` markers the frontend parses as clickable citations.

### L6 — Output (`layers/output/`)
`ExporterBase` ABC with `async def export(content, metadata) -> ExportResult`. Built-in: `FileExporter`, `WebhookExporter`, `FeishuExporter`. Extension point: `search_ghost.exporters` entry_points.

---

## Key Technical Decisions

**No external message broker**: SQLite-backed `asyncio.Queue` (`worker/queue.py`) with `aiosqlite` covers local-first use without Redis/RabbitMQ.

**ThreadPoolExecutor, not multiprocessing**: All heavy CPU work (Docling, PaddleOCR, faster-whisper) runs in `ThreadPoolExecutor`. Avoids Windows `spawn()` complexity; these C-extension libraries release the GIL.

**LanceDB = vectors + BM25**: One LanceDB table `chunks` with `vector` and `text` columns. No Elasticsearch/Meilisearch needed.

**LightRAG owns its storage**: Do not replace LightRAG's internal JSON graph files with LanceDB. `index/graph/` is included in S3 sync as-is.

**LightRAG insert**: Call `lightrag.ainsert(content_md)` with full document text — LightRAG handles its own chunking for entity extraction. Our LanceDB chunks are separate (for hybrid search).

**Dev vs prod serving**: In dev, Vite (`web/vite.config.ts`) proxies `/api/*` to FastAPI on `:8000`. In prod, `ghost serve` mounts `static/` as `StaticFiles` — no nginx needed.

---

## Tech Stack Summary

| Concern | Choice |
|---|---|
| Backend | Python 3.11+ · FastAPI · Pydantic v2 |
| LLM | LiteLLM (OpenAI · Anthropic · Gemini · Deepseek/Qwen/GLM · Ollama) |
| Vector + FTS | LanceDB (embeddable, built-in Tantivy BM25) |
| Knowledge Graph | LightRAG (`lightrag-hku`) |
| Batch Processing | Daft (PyRunner local / RayRunner distributed) |
| Document Parsing | Docling (PDF/Office) · PaddleOCR (images) · faster-whisper (audio/video) |
| Storage Abstraction | fsspec + s3fs |
| Task Queue | asyncio.Queue + aiosqlite |
| CLI | Typer |
| Package Manager | uv |
| Frontend | React 19 · TypeScript · Vite · shadcn/ui · Tailwind CSS |
| Graph Viz | react-force-graph-2d |
| API Fetching | TanStack Query · Zustand |
| File Watching | watchfiles (Rust notify, Windows-safe) |

---

## Implementation Phases

| Phase | Goal | Key additions |
|---|---|---|
| **1 — MVP** | Text search + RAG chat | KB storage, markdown parser, LanceDB hybrid search, LLM streaming, web SearchPage + IngestPage |
| **2 — Multi-modal + Daft** | PDF/images/audio + bulk ingest | Docling, PaddleOCR, Whisper, daft_pipeline.py + udfs.py, S3 support, DocumentsPage, TasksPage |
| **3 — Knowledge Graph** | LightRAG entity extraction + graph viz | graph_store.py, graph_traversal.py, GraphPage |
| **4 — Plugins + Export** | Community extensibility + output pipelines | entry_points loader, ExporterBase, FeishuExporter, SettingsPage |

---

## Frontend Structure (`web/src/`)

- `pages/`: SearchPage, DocumentsPage, IngestPage, GraphPage, TasksPage, SettingsPage
- `components/search/`: SearchBar, SearchResults, ResultCard, FilterPanel
- `components/chat/`: ChatPanel, MessageBubble, CitationChip, StreamingText
- `components/graph/`: GraphCanvas (react-force-graph-2d wrapper), NodeTooltip, GraphControls
- `api/`: TanStack Query hooks + axios client (one file per resource)
- `hooks/`: `useSSE.ts` (chat streaming), `useWebSocket.ts` (task progress)
- `stores/`: Zustand `settingsStore`, `uiStore`
