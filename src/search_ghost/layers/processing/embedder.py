"""
Embedding — calls any OpenAI-compatible /v1/embeddings endpoint directly via httpx.
Completely bypasses LiteLLM and its openai monkey-patching.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import httpx

from search_ghost.models import Chunk

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="embedder")


def _embed_sync(
    texts: list[str],
    model: str,
    api_base: str,
    api_key: str,
) -> list[list[float]]:
    # Strip provider prefix ("openai/text-embedding-v3" → "text-embedding-v3")
    model_name = model.split("/", 1)[-1] if "/" in model else model
    base = api_base.rstrip("/")

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{base}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model_name, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()

    return [item["embedding"] for item in data["data"]]


async def embed_texts(
    texts: list[str],
    model: str,
    api_base: str = "",
    api_key: str = "",
    batch_size: int = 256,
) -> list[list[float]]:
    all_embeddings: list[list[float]] = []
    loop = asyncio.get_event_loop()

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = await loop.run_in_executor(
            _executor, _embed_sync, batch, model, api_base, api_key
        )
        all_embeddings.extend(embeddings)
        logger.debug("Embedded %d/%d texts", min(i + batch_size, len(texts)), len(texts))

    return all_embeddings


async def embed_chunks(
    chunks: list[Chunk],
    model: str,
    api_base: str = "",
    api_key: str = "",
) -> list[Chunk]:
    texts = [c.text for c in chunks]
    embeddings = await embed_texts(texts, model, api_base=api_base, api_key=api_key)
    for chunk, emb in zip(chunks, embeddings):
        chunk.embedding = emb
    return chunks
