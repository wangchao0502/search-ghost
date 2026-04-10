"""Background worker — drains the TaskQueue using DirectPipeline."""

from __future__ import annotations

import asyncio
import logging

from search_ghost.kb import KnowledgeBase
from search_ghost.layers.processing.direct_pipeline import DirectPipeline

logger = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(self, kb: KnowledgeBase, concurrency: int = 4) -> None:
        self._kb = kb
        self._concurrency = concurrency
        self._pipeline = DirectPipeline(kb)
        self._semaphore = asyncio.Semaphore(concurrency)
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="background-worker")
        logger.info("BackgroundWorker started (concurrency=%d)", self._concurrency)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while True:
            task = await self._kb.task_queue.dequeue()
            asyncio.create_task(self._process(task))

    async def _process(self, task) -> None:
        async with self._semaphore:
            await self._pipeline.process(task)
