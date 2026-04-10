"""Shared Pydantic models used across all layers."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class QueryMode(str, Enum):
    HYBRID = "hybrid"
    VECTOR = "vector"
    BM25 = "bm25"


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class DocumentMeta(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    source_url: str | None = None
    content_type: str = "text/markdown"
    tags: list[str] = Field(default_factory=list)
    status: DocumentStatus = DocumentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    chunk_count: int = 0
    char_count: int = 0


class Document(BaseModel):
    meta: DocumentMeta
    content: str = ""


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------


class Chunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    embedding: list[float] | None = None


# ---------------------------------------------------------------------------
# Task (processing queue)
# ---------------------------------------------------------------------------


class ProcessingTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    progress: int = 0  # 0-100


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float
    doc_title: str | None = None
    source_url: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


class IngestResponse(BaseModel):
    task_id: str
    doc_id: str
    message: str = "Ingestion queued"


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    query_mode: QueryMode = QueryMode.HYBRID
    top_k: int = 6
    stream: bool = True


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class KBConfig(BaseModel):
    name: str = "default"
    schema_version: str = "1.0"
    embedding_model: str = "openai/text-embedding-3-small"
    llm_model: str = "openai/gpt-4o-mini"
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 6
    rrf_k: int = 60
    extra: dict[str, Any] = Field(default_factory=dict)
