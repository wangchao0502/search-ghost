"""Markdown / plain-text parser (Phase 1)."""

from __future__ import annotations

import re

from search_ghost.layers.processing.parsers.registry import register


@register("text/markdown")
@register("text/plain")
@register("text/x-markdown")
class MarkdownParser:
    def parse(self, data: bytes, filename: str) -> str:
        text = data.decode("utf-8", errors="replace")
        # Strip HTML tags if any slipped through
        text = re.sub(r"<[^>]+>", "", text)
        # Normalise line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text.strip()
