"""
STT service client — calls ml:5001/stt (faster-whisper).
Groq Whisper fires only on local failure.
"""

from __future__ import annotations

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

logger = logging.getLogger("lipi.backend.stt")


async def _local_transcribe(
    audio_bytes: bytes,
    http: httpx.AsyncClient,
    *,
    prompt: str | None = None,
    language_hint: str | None = None,
) -> dict:
    resp = await http.post(
        f"{settings.ml_service_url}/stt",
        files={"audio": ("audio.webm", audio_bytes, "audio/webm")},
        data={
            "prompt": prompt or "",
            "language_hint": language_hint or "",
        },
        timeout=settings.ml_timeout,
    )
    resp.raise_for_status()
    return resp.json()  # {text, language, confidence, duration_ms}


@retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    reraise=True,
)
async def _groq_transcribe(
    audio_bytes: bytes,
    http: httpx.AsyncClient,
    *,
    prompt: str | None = None,
) -> dict:
    """Groq Whisper fallback."""
    if not settings.groq_api_key:
        raise RuntimeError("Groq API key not configured — no STT fallback")

    logger.warning("Local STT unavailable — routing to Groq Whisper fallback")

    resp = await http.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        files={"file": ("audio.webm", audio_bytes, "audio/webm")},
        data={
            "model": "whisper-large-v3",
            "response_format": "verbose_json",
            "prompt": prompt or "",
        },
        timeout=20.0,
    )
    resp.raise_for_status()
    body = resp.json()
    return {
        "text": body.get("text", ""),
        "language": body.get("language", "ne"),
        "confidence": 0.9,   # Groq doesn't expose per-segment confidence
        "duration_ms": 0,
    }


async def transcribe(
    audio_bytes: bytes,
    http: httpx.AsyncClient,
    *,
    prompt: str | None = None,
    language_hint: str | None = None,
) -> dict:
    """Transcribe audio. Returns {text, language, confidence, duration_ms}."""
    try:
        return await _local_transcribe(audio_bytes, http, prompt=prompt, language_hint=language_hint)
    except Exception as exc:
        if not settings.groq_api_key:
            logger.error("Local STT error with no Groq fallback configured: %s", exc)
            raise
        logger.warning("Local STT error (%s), activating Groq fallback", exc)
        return await _groq_transcribe(audio_bytes, http, prompt=prompt)
