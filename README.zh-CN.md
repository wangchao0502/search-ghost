# search-ghost

**本地优先的个人知识库** — 支持多模态导入、混合检索、可选知识图谱，以及基于大模型的 RAG 对话。知识库是一个可移植的目录；存储可在本地或通过 [fsspec](https://filesystem-spec.readthedocs.io/) 对接 S3 兼容对象存储。

**语言：** [English](README.md) · [简体中文](README.zh-CN.md)

## 功能概览

- **混合检索** — 在 [LanceDB](https://lancedb.github.io/lancedb/) 中结合 BM25 与稠密向量，RRF 融合
- **RAG 对话** — 通过 [LiteLLM](https://github.com/BerriAI/litellm) 流式输出，并附带引用
- **Web + CLI** — FastAPI 后端、React（Vite）前端；`ghost` Typer 命令行支持 serve / ingest / search / chat
- **可移植 KB 结构** — `.ghost/config`、SQLite 任务队列、`documents/`、`chunks/`、`index/vectors.lance/`
- **路线图** — 多模态解析器、Daft 批处理、LightRAG 图谱等，详见 [SPEC.md](SPEC.md)

## 环境要求

- **Python** 3.11+（推荐使用 [uv](https://github.com/astral-sh/uv) 管理）
- **Node.js** + **pnpm** — 仅用于 `web/` 前端

## 快速开始

### 1. 安装依赖

```bash
uv sync
cd web && pnpm install
```

### 2. 配置环境变量

在项目根目录创建 `.env`（或自行 export）。应用配置均使用 `GHOST_` 前缀：

| 变量 | 说明 |
|------|------|
| `GHOST_KB_PATH` | 知识库根目录（默认 `./kb`；后续可支持 `s3://...`） |
| `GHOST_LLM_MODEL` | LiteLLM 模型 id（默认 `openai/gpt-4o-mini`） |
| `GHOST_LLM_API_KEY` | 大模型 API 密钥（也可使用 `OPENAI_API_KEY` 等） |
| `GHOST_LLM_API_BASE` | 可选的自定义 API 基地址 |
| `GHOST_EMBEDDING_MODEL` | 嵌入模型（默认 `openai/text-embedding-3-small`） |
| `GHOST_EMBEDDING_API_KEY` | 嵌入专用密钥（若与 LLM 不同） |
| `GHOST_EMBEDDING_API_BASE` | 可选的嵌入 API 基地址 |

分块大小、检索 `top_k`、Worker 并发等更多项见 `src/search_ghost/config.py`。

### 3. 启动后端

```bash
uv run uvicorn search_ghost.main:app --reload --port 8000
```

或使用 CLI：

```bash
uv run ghost serve --kb-path ./my-kb
```

### 4. 启动前端（开发）

```bash
cd web && pnpm dev
```

Vite 开发服务器会将 `/api/*` 代理到后端（8000 端口）。

### 5. 生产环境静态资源

```bash
cd web && pnpm build
```

`ghost serve` 可从 `static/` 提供构建产物，便于类生产部署。

## 命令行

```bash
uv run ghost --help
uv run ghost serve --kb-path ./my-kb
uv run ghost ingest <文件>
uv run ghost ingest ./目录/   # 目录下全部文件
uv run ghost search "检索内容"
uv run ghost chat "你的问题"
```

## 可选依赖组

在 `pyproject.toml` 中定义：

| 组 | 用途 |
|----|------|
| `multimodal` | Docling、PaddleOCR、faster-whisper（规划中的解析器） |
| `distributed` | Daft + Ray 批处理 |
| `graph` | LightRAG 知识图谱 |
| `dev` | pytest、ruff、mypy |

示例：

```bash
uv sync --extra dev --extra graph
```

## 开发

```bash
uv run pytest
uv run ruff check src/ && uv run ruff format src/
uv run mypy src/search_ghost/
```

## 文档

- **[CLAUDE.md](CLAUDE.md)** — 架构分层（L1–L6）、技术栈与贡献约定（英文）
- **[SPEC.md](SPEC.md)** — 分阶段路线图与任务清单（中文为主）

## 目录结构（简表）

| 路径 | 作用 |
|------|------|
| `src/search_ghost/` | Python 包 — API、CLI、各处理层 |
| `web/` | React + Vite 前端 |
| `tests/` | Pytest 测试 |

---

*search-ghost — 在自有文档上完成导入、检索与对话，尽可能本地优先。*
