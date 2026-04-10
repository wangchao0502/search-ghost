"""
Parser registry — MIME-type keyed.
Extension point: register via search_ghost.parsers entry_points.
"""

from __future__ import annotations

from typing import Callable, Protocol


class Parser(Protocol):
    def parse(self, data: bytes, filename: str) -> str:
        """Return plain text / Markdown from raw bytes."""
        ...


_REGISTRY: dict[str, Parser] = {}


def register(mime_type: str) -> Callable[[type], type]:
    def decorator(cls: type) -> type:
        _REGISTRY[mime_type] = cls()
        return cls

    return decorator


def get_parser(mime_type: str) -> Parser | None:
    # Exact match first
    if mime_type in _REGISTRY:
        return _REGISTRY[mime_type]
    # Prefix match (e.g. "text/" catches "text/plain", "text/markdown")
    prefix = mime_type.split("/")[0] + "/"
    for key, parser in _REGISTRY.items():
        if key.startswith(prefix):
            return parser
    return None


def get_parser_registry() -> dict[str, Parser]:
    return dict(_REGISTRY)


# Import built-in parsers so they register themselves
from search_ghost.layers.processing.parsers import markdown  # noqa: E402, F401
