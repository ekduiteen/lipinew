"""
TTS service client — calls ml:5001/tts (facebook/mms-tts-npi).
No Groq fallback for TTS — return silence bytes on failure.
"""

from __future__ import annotations

import logging
import struct
import wave
import io

import httpx

from config import settings

logger = logging.getLogger("lipi.backend.tts")

_SAMPLE_RATE = 16000


def _silent_wav(duration_ms: int = 300) -> bytes:
    """Return a minimal WAV with silence — used as fallback."""
    num_samples = int(_SAMPLE_RATE * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    return buf.getvalue()


async def synthesize(text: str, http: httpx.AsyncClient, language: str = "ne") -> bytes:
    """
    Synthesize speech. Returns raw WAV bytes.
    On failure returns 300ms of silence so the WebSocket flow doesn't stall.
    """
    if not text.strip():
        return _silent_wav()
    try:
        resp = await http.post(
            f"{settings.ml_service_url}/tts",
            json={"text": text, "language": language},
            timeout=settings.ml_timeout,
        )
        resp.raise_for_status()
        return resp.content  # WAV bytes
    except Exception as exc:
        logger.warning("TTS failed (%s) — returning silence", exc)
        return _silent_wav()
