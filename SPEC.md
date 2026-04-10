# search-ghost — 开发规划 (SPEC / TODOLIST)

> 本文件是项目的权威任务清单，每个阶段完成后及时更新状态。
> 架构细节请参见 [CLAUDE.md](./CLAUDE.md)。

---

## 阶段总览

| Phase | 目标 | 状态 |
|---|---|---|
| **1 — MVP** | 文本搜索 + RAG 对话 | ✅ 完成 |
| **2 — 多模态 + 批处理** | PDF/图片/音频 + 大批量导入 | 🔲 待开始 |
| **3 — 知识图谱** | LightRAG 实体提取 + 图谱可视化 | 🔲 待开始 |
| **4 — 插件 + 导出** | 社区扩展点 + 输出管道 | 🔲 待开始 |

---

## Phase 1 — MVP ✅

### 后端
- [x] `pyproject.toml` — 依赖声明、entry_points 占位、pytest/ruff/mypy 配置
- [x] `src/search_ghost/config.py` — `Settings`（pydantic-settings，`GHOST_` 前缀，支持 `.env`）
- [x] `src/search_ghost/models.py` — 所有共享 Pydantic 模型（Document、Chunk、Task、SearchResult 等）
- [x] `src/search_ghost/kb.py` — `KnowledgeBase` 根对象，聚合所有 store
- [x] `src/search_ghost/deps.py` — FastAPI DI，`KBDep`
- [x] `src/search_ghost/main.py` — FastAPI 应用，lifespan，CORS，静态文件挂载
- [x] `src/search_ghost/cli.py` — Typer CLI（`ghost serve / ingest / search / chat`）
- [x] L1 `layers/ingestion/router.py` — 文件上传 `/api/ingest`，文本 `/api/ingest/text`
- [x] L2 `layers/processing/chunker.py` — 递归字符分割，段落→句→词边界
- [x] L2 `layers/processing/embedder.py` — httpx 直调 `/v1/embeddings`，批量，ThreadPoolExecutor
- [x] L2 `layers/processing/parsers/registry.py` — MIME 键控注册表，`@register()` 装饰器
- [x] L2 `layers/processing/parsers/markdown.py` — Markdown/纯文本解析器
- [x] L2 `layers/processing/direct_pipeline.py` — 单文档异步流水线（parse→chunk→embed→store）
- [x] L3 `layers/storage/object_store.py` — fsspec 封装（本地/S3 透明切换）
- [x] L3 `layers/storage/document_store.py` — 文档 CRUD（meta.json / content.md / raw/）
- [x] L3 `layers/storage/vector_store.py` — LanceDB 封装：向量写入、BM25 FTS、向量搜索
- [x] L4 `layers/retrieval/hybrid_search.py` — BM25 + 向量并行搜索，RRF 融合
- [x] L5 `layers/generation/llm_client.py` — LiteLLM 流式/非流式，config-driven
- [x] L5 `layers/generation/citation_builder.py` — 上下文拼装，系统提示，引用格式
- [x] L5 `layers/generation/rag_pipeline.py` — retrieve→assemble→stream，SSE 事件流
- [x] `api/search.py` — `GET /api/search`（hybrid/vector/bm25 模式）
- [x] `api/chat.py` — `POST /api/chat`（SSE 流式 RAG）
- [x] `api/documents.py` — `GET/DELETE /api/documents`
- [x] `api/tasks.py` — `GET /api/tasks`，`GET /api/tasks/{id}`
- [x] `worker/queue.py` — SQLite 持久化任务队列，重启恢复
- [x] `worker/worker.py` — 并发后台 worker，Semaphore 限流

### 前端
- [x] Vite + React 19 + TypeScript + Tailwind + TanStack Query 脚手架
- [x] `web/src/api/client.ts` — axios 客户端 + 全部类型定义
- [x] `pages/SearchPage.tsx` — 搜索栏、结果卡片、"Ask about this" 快捷入口
- [x] `components/chat/ChatPanel.tsx` — SSE 流式对话，sources 引用气泡
- [x] `pages/IngestPage.tsx` — 拖拽上传，多文件，实时状态
- [x] `pages/DocumentsPage.tsx` — 文档列表，状态徽章，删除
- [x] `pages/TasksPage.tsx` — 任务列表，进度条，3s 轮询

### 测试
- [x] `tests/unit/test_chunker.py`
- [x] `tests/unit/test_hybrid_search.py`（RRF 逻辑）
- [x] `tests/unit/test_markdown_parser.py`

---

## Phase 2 — 多模态 + 批处理 🔲

> 目标：支持 PDF/Office/图片/音频，并提供 `ghost ingest --batch` 大批量路径。

### 后端

#### 新解析器（`layers/processing/parsers/`）
- [ ] `docling_parser.py` — Docling 解析 PDF/DOCX/PPTX（`application/pdf`、`application/vnd.*`）
  - 注册为 `application/pdf`、`application/vnd.openxmlformats-officedocument.*`
  - 使用 `DocumentConverter`，返回 Markdown 字符串
- [ ] `paddleocr_parser.py` — PaddleOCR 解析图片（`image/*`）
  - 注册为 `image/png`、`image/jpeg`、`image/webp` 等
  - 线程本地模型实例（`threading.local()`）避免重复初始化
- [ ] `whisper_parser.py` — faster-whisper 解析音频/视频（`audio/*`、`video/*`）
  - 注册为 `audio/mpeg`、`audio/wav`、`video/mp4` 等
  - 先用 ffmpeg 提取音频流再转写

#### Daft 批处理流水线（`layers/processing/`）
- [ ] `udfs.py` — Daft 有状态 UDF
  - `ParseUDF` — 每 partition 初始化一次解析器注册表
  - `EmbedUDF` — 每 partition 初始化一次 httpx 客户端，批量嵌入
- [ ] `daft_pipeline.py` — `DaftPipeline` 类
  - `process_batch(tasks)` — 构建 Daft DataFrame，链式 UDF，结果写回 LanceDB + DocumentStore
  - `GHOST_DAFT_RUNNER=ray` 时自动切换 RayRunner，零代码改动
- [ ] `direct_pipeline.py` 增强 — 注册新 MIME 类型解析器后自动生效（无需改动流水线）
- [ ] `worker/worker.py` 增强 — 批任务达到 `BATCH_THRESHOLD`（默认 8）时切换至 DaftPipeline

#### S3 支持
- [ ] `object_store.py` — 验证 `s3://` 路径下的全路径 I/O（需 `s3fs` 凭证配置）
- [ ] `vector_store.py` — LanceDB S3 URI 直通（LanceDB 原生支持，配置 `GHOST_KB_PATH=s3://...` 即可）
- [ ] `.env.example` 补充 S3 相关变量（`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_DEFAULT_REGION`）

#### API 扩展
- [ ] `api/ingest.py` — 扩展 `accept` 类型到 PDF/图片/音频（multipart 上传限制调大）
- [ ] `api/documents.py` — 返回 `content_type` 字段供前端展示图标

### 前端
- [ ] `pages/IngestPage.tsx` — 去掉 Phase 1 的 `.md/.txt` 限制，接受所有文件类型
- [ ] `components/DocumentIcon.tsx` — 按 MIME 显示 PDF/图片/音频图标
- [ ] `pages/DocumentsPage.tsx` — 展示文件类型图标

### 测试
- [ ] `tests/unit/test_daft_pipeline.py` — mock UDF，验证 DataFrame 构建逻辑
- [ ] `tests/integration/test_pdf_ingest.py` — 小 PDF 端到端（需 Docling 安装）

---

## Phase 3 — 知识图谱 🔲

> 目标：LightRAG 实体/关系抽取 + 图谱可视化页面。

### 后端

#### 图谱存储（`layers/storage/`）
- [ ] `graph_store.py` — 封装 `lightrag-hku` 的初始化和 insert
  - `working_dir` 指向 `{kb-root}/index/graph/`
  - `KnowledgeBase.graph_store` 字段
  - `await graph_store.insert(content_md)` — LightRAG 自己做 NER chunking

#### 图谱检索（`layers/retrieval/`）
- [ ] `graph_traversal.py` — `GraphRetriever`
  - `aquery(query, mode)` — 封装 `lightrag.aquery(mode="hybrid")`
  - 支持 `naive / local / global / hybrid` 四种模式
  - 返回标准化 `SearchResult` 列表（带 entity 元数据）

#### 流水线集成
- [ ] `direct_pipeline.py` — step 6：处理完成后调用 `graph_store.insert(content_md)`（可配置开关 `GHOST_GRAPH_ENABLED`）
- [ ] `daft_pipeline.py` — 批处理完成后异步 insert 图谱

#### API
- [ ] `api/graph.py` — `GET /api/graph` 返回实体/关系 JSON（供 react-force-graph-2d 使用）
- [ ] `api/search.py` — `mode=graph` 时调用 `GraphRetriever.aquery()`
- [ ] `rag_pipeline.py` — `QueryMode.GRAPH` 走图谱检索路径

#### KB 初始化
- [ ] `kb.py` — 条件初始化 `GraphStore`（`GHOST_GRAPH_ENABLED=true` 时）

### 前端
- [ ] 安装 `react-force-graph-2d`（`pnpm add react-force-graph-2d`）
- [ ] `pages/GraphPage.tsx` — 图谱主页
- [ ] `components/graph/GraphCanvas.tsx` — react-force-graph-2d 封装，节点/边渲染
- [ ] `components/graph/NodeTooltip.tsx` — hover 显示实体详情
- [ ] `components/graph/GraphControls.tsx` — 搜索节点、切换布局、缩放重置
- [ ] `App.tsx` — 添加 Graph 导航项（Network 图标）
- [ ] `api/client.ts` — 添加 `fetchGraph()` API 方法

### 测试
- [ ] `tests/unit/test_graph_traversal.py` — mock LightRAG，验证 mode 映射
- [ ] `tests/integration/test_graph_insert.py` — 小文档 insert + 实体查询

---

## Phase 4 — 插件 + 导出 🔲

> 目标：社区可扩展的 ingestor/parser/exporter + 输出管道。

### 后端

#### 导出层（`layers/output/`）
- [ ] `base.py` — `ExporterBase` ABC
  ```python
  class ExporterBase(ABC):
      @abstractmethod
      async def export(self, content: str, metadata: dict) -> ExportResult: ...
  ```
- [ ] `file_exporter.py` — 导出到本地文件（Markdown/JSON）
- [ ] `webhook_exporter.py` — HTTP POST 到任意 webhook
- [ ] `feishu_exporter.py` — 飞书卡片消息（通过飞书 Bot webhook）
- [ ] `loader.py` — `search_ghost.exporters` entry_points 加载器

#### 插件加载器统一化
- [ ] `layers/ingestion/` — entry_points 加载 `search_ghost.ingestors`
- [ ] `layers/processing/parsers/loader.py` — entry_points 加载 `search_ghost.parsers`
- [ ] `pyproject.toml` — 补充 entry_points 示例注释

#### API
- [ ] `api/export.py` — `POST /api/export`（选择 exporter + 文档 ID）
- [ ] `api/settings.py` — `GET/POST /api/settings`（读写 `.ghost/config.json`）

### 前端
- [ ] `pages/SettingsPage.tsx`
  - LLM 模型、API Key、Embedding 模型配置
  - KB 路径、S3 凭证
  - 导出配置（飞书 webhook URL 等）
- [ ] `App.tsx` — 添加 Settings 导航项（Settings 图标）
- [ ] `api/client.ts` — 添加 `getSettings() / updateSettings()` API 方法

### 测试
- [ ] `tests/unit/test_exporters.py` — FileExporter + WebhookExporter（mock httpx）
- [ ] `tests/unit/test_plugin_loader.py` — entry_points 加载机制

---

## 横切关注点（贯穿各阶段）

### 代码质量
- [ ] `ruff check src/` 零警告
- [ ] `mypy src/search_ghost/` 无 error（strict=false）
- [ ] 所有公开函数有 docstring

### 文档
- [ ] `README.md` — 完整快速开始、架构图、配置参考
- [ ] `docs/api.md` — OpenAPI 端点说明（可由 `/docs` 自动生成）
- [ ] `docs/plugin-guide.md` — 自定义 ingestor/parser/exporter 教程

### 基础设施
- [ ] `.github/workflows/ci.yml` — pytest + ruff + mypy + pnpm build
- [ ] `Dockerfile` — 多阶段构建（uv + pnpm build → 最小运行时镜像）
- [ ] `docker-compose.yml` — 一键启动（含环境变量模板）

---

## 近期行动项（下一个工作日）

按优先级排序，每次会话聚焦一个条目：

1. **[ ] Phase 2 — Docling 解析器** (`parsers/docling_parser.py`)
   - 实现、注册 MIME、单元测试（mock Docling）
2. **[ ] Phase 2 — PaddleOCR 解析器** (`parsers/paddleocr_parser.py`)
3. **[ ] Phase 2 — Whisper 解析器** (`parsers/whisper_parser.py`)
4. **[ ] Phase 2 — Daft UDFs + DaftPipeline**
5. **[ ] Phase 2 — Worker 批量路由**（达到 `BATCH_THRESHOLD` 切换 DaftPipeline）
6. **[ ] Phase 3 — GraphStore + GraphTraversal**
7. **[ ] Phase 3 — GraphPage 前端**
8. **[ ] Phase 4 — ExporterBase + FeishuExporter**
9. **[ ] Phase 4 — SettingsPage**
10. **[ ] CI/CD — GitHub Actions workflow**
