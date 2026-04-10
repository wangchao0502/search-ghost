"""FastAPI dependency injection for KnowledgeBase."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from search_ghost.kb import KnowledgeBase


def get_kb(request: Request) -> KnowledgeBase:
    return request.app.state.kb


KBDep = Annotated[KnowledgeBase, Depends(get_kb)]
