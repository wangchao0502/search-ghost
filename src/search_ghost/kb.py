"""
KnowledgeBase — root object that owns all stores.
Injected via FastAPI DI (deps.py).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from search_ghost.config import Settings
from search_ghost.layers.storage.document_store import DocumentStore
from search_ghost.layers.storage.object_store import ObjectStore
from search_ghost.layers.storage.vector_store import VectorStore
from search_ghost.models import KBConfig
from search_ghost.worker.queue import TaskQueue

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.kb_path

        # Core stores
        self.object_store = ObjectStore(self.root)

        # LanceDB path (always local for now; S3 via fsspec wrapper later)
        lance_path = str(Path(self.root) / "index" / "vectors.lance")
        self.vector_store = VectorStore(lance_path, dim=settings.embedding_dim)

        self.document_store = DocumentStore(self.object_store)

        db_path = str(Path(self.root) / ".ghost" / "task_queue.db")
        self.task_queue = TaskQueue(db_path)

        self._config: KBConfig | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Call once on startup."""
        self._ensure_structure()
        await self.task_queue.initialize()
        await self.vector_store.initialize()
        logger.info("KnowledgeBase initialized at %s", self.root)

    async def close(self) -> None:
        await self.task_queue.close()

    # ------------------------------------------------------------------
    # KB config
    # ------------------------------------------------------------------

    def _ensure_structure(self) -> None:
        ghost_dir = Path(self.root) / ".ghost"
        ghost_dir.mkdir(parents=True, exist_ok=True)
        config_path = ghost_dir / "config.json"
        if not config_path.exists():
            cfg = KBConfig(
                name=Path(self.root).name,
                embedding_model=self.settings.embedding_model,
                llm_model=self.settings.llm_model,
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )
            config_path.write_text(json.dumps(cfg.model_dump(mode="json"), indent=2))

    @property
    def config(self) -> KBConfig:
        if self._config is None:
            config_path = Path(self.root) / ".ghost" / "config.json"
            self._config = KBConfig.model_validate(json.loads(config_path.read_text()))
        return self._config
