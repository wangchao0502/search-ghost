# search-ghost

**Local-first personal knowledge base** — multi-modal ingest, hybrid search, optional knowledge graph, and LLM-powered RAG chat. Your KB is a portable folder; storage can be local or S3-compatible via [fsspec](https://filesystem-spec.readthedocs.io/).

**Languages:** [English](README.md) · [简体中文](README.zh-CN.md)

## Features

- **Hybrid retrieval** — BM25 + dense vectors in [LanceDB](https://lancedb.github.io/lancedb/), fused with RRF
- **RAG chat** — Streaming answers with citations via [LiteLLM](https://github.com/BerriAI/litellm)
- **Web UI + CLI** — FastAPI backend, React (Vite) frontend; `ghost` Typer CLI for serve / ingest / search / chat
- **Portable KB layout** — `.ghost/config`, SQLite task queue, `documents/`, `chunks/`, `index/vectors.lance/`
- **Roadmap** — Multi-modal parsers, Daft batch pipeline, LightRAG graph (see [SPEC.md](SPEC.md))

## Requirements

- **Python** 3.11+ (managed with [uv](https://github.com/astral-sh/uv))
- **Node.js** + **pnpm** — for the `web/` frontend only

## Quick start

### 1. Install dependencies

```bash
uv sync
cd web && pnpm install
```

### 2. Configure environment

Create a `.env` in the project root (or export variables). All app settings use the `GHOST_` prefix:

| Variable | Description |
|----------|-------------|
| `GHOST_KB_PATH` | Knowledge base root (default `./kb`; can be `s3://...` when supported) |
| `GHOST_LLM_MODEL` | LiteLLM model id (default `openai/gpt-4o-mini`) |
| `GHOST_LLM_API_KEY` | API key for the LLM (or use `OPENAI_API_KEY` / provider-specific vars) |
| `GHOST_LLM_API_BASE` | Optional custom API base URL |
| `GHOST_EMBEDDING_MODEL` | Embedding model (default `openai/text-embedding-3-small`) |
| `GHOST_EMBEDDING_API_KEY` | Embedding API key if different from LLM |
| `GHOST_EMBEDDING_API_BASE` | Optional embedding API base URL |

See `src/search_ghost/config.py` for chunk sizes, retrieval `top_k`, worker concurrency, and more.

### 3. Run the backend

```bash
uv run uvicorn search_ghost.main:app --reload --port 8000
```

Or use the CLI:

```bash
uv run ghost serve --kb-path ./my-kb
```

### 4. Run the frontend (development)

```bash
cd web && pnpm dev
```

The Vite dev server proxies `/api/*` to the backend (port 8000).

### 5. Production static build

```bash
cd web && pnpm build
```

`ghost serve` can serve the built assets from `static/` for production-style deployment.

## CLI

```bash
uv run ghost --help
uv run ghost serve --kb-path ./my-kb
uv run ghost ingest <file>
uv run ghost ingest ./folder/   # all files under directory
uv run ghost search "your query"
uv run ghost chat "your question"
```

## Optional dependency groups

Defined in `pyproject.toml`:

| Group | Purpose |
|-------|---------|
| `multimodal` | Docling, PaddleOCR, faster-whisper (planned parsers) |
| `distributed` | Daft + Ray for batch processing |
| `graph` | LightRAG for knowledge graph |
| `dev` | pytest, ruff, mypy |

Example:

```bash
uv sync --extra dev --extra graph
```

## Development

```bash
uv run pytest
uv run ruff check src/ && uv run ruff format src/
uv run mypy src/search_ghost/
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** — Architecture layers (L1–L6), stack, and conventions for contributors
- **[SPEC.md](SPEC.md)** — Phased roadmap and task checklist

## Project layout (short)

| Path | Role |
|------|------|
| `src/search_ghost/` | Python package — API, CLI, layers (ingestion → output) |
| `web/` | React + Vite frontend |
| `tests/` | Pytest suite |

---

*search-ghost — ingest, search, and chat over your own documents, offline-first where possible.*
