"""
Builds citation context from search results and parses [source:uuid] markers.
"""

from __future__ import annotations

from search_ghost.models import SearchResult

SYSTEM_PROMPT = """You are a helpful assistant for a personal knowledge base.
Answer the user's question using only the provided context.
For each piece of information you use, append a citation in the format [source:{chunk_id}].
If the context doesn't contain enough information, say so honestly.
Be concise and accurate."""


def build_context(results: list[SearchResult]) -> str:
    """Format search results as numbered context blocks."""
    parts: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.doc_title or r.doc_id
        parts.append(f"[{i}] (chunk_id: {r.chunk_id}, source: {title})\n{r.text}")
    return "\n\n---\n\n".join(parts)


def build_messages(
    user_messages: list[dict],
    context: str,
) -> list[dict]:
    """Prepend system prompt + context to the conversation."""
    system = SYSTEM_PROMPT
    if context:
        system += f"\n\n## Retrieved Context\n\n{context}"
    return [{"role": "system", "content": system}] + user_messages
