"""
LiteLLM wrapper — streaming + non-streaming completions.
Provider is purely config-driven; zero code change to switch models.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

import litellm

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True


async def stream_completion(
    messages: list[dict],
    model: str,
    api_base: str = "",
    api_key: str = "",
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """Yield text delta chunks from a streaming LLM response."""
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    response = await litellm.acompletion(**kwargs)
    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


async def complete(
    messages: list[dict],
    model: str,
    api_base: str = "",
    api_key: str = "",
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    """Non-streaming completion — returns full response text."""
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content or ""
