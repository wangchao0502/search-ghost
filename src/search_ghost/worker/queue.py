"""
SQLite-backed async task queue.
Survives restarts: pending/processing tasks are recovered on startup.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import aiosqlite

from search_ghost.models import ProcessingTask, TaskStatus

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id     TEXT PRIMARY KEY,
    doc_id      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT NOT NULL,
    started_at  TEXT,
    completed_at TEXT,
    error       TEXT,
    progress    INTEGER NOT NULL DEFAULT 0
)
"""


class TaskQueue:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._queue: asyncio.Queue[ProcessingTask] = asyncio.Queue()
        self._db: aiosqlite.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(CREATE_TABLE)
        await self._db.commit()
        await self._recover_pending()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def _recover_pending(self) -> None:
        """Re-queue tasks that were pending/processing when the server last stopped."""
        async with self._db.execute(
            "SELECT * FROM tasks WHERE status IN ('pending', 'processing')"
        ) as cur:
            rows = await cur.fetchall()
        for row in rows:
            task = self._row_to_task(dict(row))
            task.status = TaskStatus.PENDING
            await self._queue.put(task)
        if rows:
            logger.info("Recovered %d pending tasks from DB", len(rows))

    # ------------------------------------------------------------------
    # Enqueue / dequeue
    # ------------------------------------------------------------------

    async def enqueue(self, task: ProcessingTask) -> None:
        await self._persist(task)
        await self._queue.put(task)

    async def dequeue(self) -> ProcessingTask:
        task = await self._queue.get()
        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.utcnow()
        await self._persist(task)
        return task

    # ------------------------------------------------------------------
    # Status updates
    # ------------------------------------------------------------------

    async def mark_completed(self, task_id: str) -> None:
        await self._update(task_id, status=TaskStatus.COMPLETED, completed_at=datetime.utcnow(), progress=100)

    async def mark_failed(self, task_id: str, error: str) -> None:
        await self._update(task_id, status=TaskStatus.FAILED, error=error, completed_at=datetime.utcnow())

    async def update_progress(self, task_id: str, progress: int) -> None:
        await self._update(task_id, progress=progress)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_task(self, task_id: str) -> ProcessingTask | None:
        async with self._db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return self._row_to_task(dict(row))

    async def list_tasks(self, limit: int = 50) -> list[ProcessingTask]:
        async with self._db.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_task(dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _row_to_task(self, row: dict) -> ProcessingTask:
        return ProcessingTask(
            task_id=row["task_id"],
            doc_id=row["doc_id"],
            status=TaskStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
            progress=row["progress"] or 0,
        )

    async def _persist(self, task: ProcessingTask) -> None:
        await self._db.execute(
            """
            INSERT OR REPLACE INTO tasks
              (task_id, doc_id, status, created_at, started_at, completed_at, error, progress)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.task_id,
                task.doc_id,
                task.status.value,
                task.created_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                task.error,
                task.progress,
            ),
        )
        await self._db.commit()

    async def _update(self, task_id: str, **fields: object) -> None:
        set_parts = ", ".join(f"{k} = ?" for k in fields)
        values = []
        for v in fields.values():
            if isinstance(v, datetime):
                values.append(v.isoformat())
            elif isinstance(v, TaskStatus):
                values.append(v.value)
            else:
                values.append(v)
        values.append(task_id)
        await self._db.execute(f"UPDATE tasks SET {set_parts} WHERE task_id = ?", values)
        await self._db.commit()
