"""
LLM service — vLLM primary, Groq fallback (circuit breaker pattern).
Never call Groq directly; it only fires when local vLLM fails.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import settings

logger = logging.getLogger("lipi.backend.llm")


# ─── vLLM (primary) ─────────────────────────────────────────────────────────

async def _vllm_stream(
    messages: list[dict],
    http: httpx.AsyncClient,
) -> AsyncIterator[str]:
    """Stream token deltas from local vLLM (OpenAI-compatible SSE)."""
    payload = {
        "model": settings.vllm_model,
        "messages": messages,
        "stream": True,
        "max_tokens": 256,
        "temperature": 0.8,
    }
    async with http.stream(
        "POST",
        f"{settings.vllm_url}/v1/chat/completions",
        json=payload,
        timeout=settings.vllm_timeout,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            import json
            chunk = json.loads(data)
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                yield delta


async def _vllm_complete(
    messages: list[dict],
    http: httpx.AsyncClient,
) -> str:
    """Non-streaming vLLM completion — used internally by fallback wrapper."""
    chunks: list[str] = []
    async for token in _vllm_stream(messages, http):
        chunks.append(token)
    return "".join(chunks)


# ─── Groq fallback ───────────────────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    reraise=True,
)
async def _groq_complete(
    messages: list[dict],
    http: httpx.AsyncClient,
) -> str:
    """Groq fallback — fires ONLY when local vLLM fails."""
    if not settings.groq_api_key:
        raise RuntimeError("Groq API key not configured — no fallback available")

    logger.warning("vLLM unavailable — routing to Groq fallback")

    resp = await http.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": 256,
            "temperature": 0.8,
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ─── Public interface ────────────────────────────────────────────────────────

async def generate(
    messages: list[dict],
    http: httpx.AsyncClient,
    *,
    stream: bool = False,
) -> str | AsyncIterator[str]:
    """
    Generate a response from vLLM with automatic Groq fallback.

    Pass stream=True to get an async iterator of token deltas (vLLM only;
    fallback always returns a complete string).
    """
    try:
        if stream:
            # Caller gets the iterator; exceptions surface during iteration.
            # Wrap in a guarded generator so fallback still works.
            return _guarded_stream(messages, http)
        return await _vllm_complete(messages, http)
    except Exception as exc:
        logger.warning("vLLM error (%s), activating Groq fallback", exc)
        return await _groq_complete(messages, http)


async def _guarded_stream(
    messages: list[dict],
    http: httpx.AsyncClient,
) -> AsyncIterator[str]:
    """Stream from vLLM; on any error fall back to a single Groq chunk."""
    try:
        async for token in _vllm_stream(messages, http):
            yield token
    except Exception as exc:
        logger.warning("vLLM stream error (%s), falling back to Groq", exc)
        text = await _groq_complete(messages, http)
        yield text
