"""Tasks API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from search_ghost.deps import KBDep
from search_ghost.models import ProcessingTask

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[ProcessingTask])
async def list_tasks(kb: KBDep, limit: int = 50) -> list[ProcessingTask]:
    return await kb.task_queue.list_tasks(limit=limit)


@router.get("/{task_id}", response_model=ProcessingTask)
async def get_task(task_id: str, kb: KBDep) -> ProcessingTask:
    task = await kb.task_queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
