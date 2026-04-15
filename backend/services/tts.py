"""
TTS service client — calls ml:5001/tts.

Pipeline:
    text  →  clean_for_tts()  →  POST ml:5001/tts  →  WAV bytes

clean_for_tts() strips markdown, brackets, URLs, and ellipsis so the TTS
engine never speaks formatting noise.  Content-level cleanup (sentence limits,
filler removal) is done earlier by response_cleanup.finalize_reply() in
sessions.py before this function is ever called.

On any failure returns empty bytes — the caller surfaces an honest
"no audio" state rather than pretending playback happened.
"""

from __future__ import annotations

import logging
import re
import struct
import io
import wave

import httpx

from config import settings
from services.response_cleanup import clean_for_tts

logger = logging.getLogger("lipi.backend.tts")

_SAMPLE_RATE = 16_000
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def _silent_wav(duration_ms: int = 300) -> bytes:
    """Return a minimal WAV with silence (used by local testing utilities)."""
    num_samples = int(_SAMPLE_RATE * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    return buf.getvalue()


def _infer_tts_language(text: str, fallback_language: str) -> str:
    """Resolve a canonical language code for the TTS service."""
    explicit = (fallback_language or "").lower()
    if explicit in {"en", "english"}:
        return "en"
    if explicit in {"ne", "new", "newari", "nepali"}:
        return "ne"
    if explicit == "mixed":
        # Mixed turns: use Nepali if Devanagari is present, English otherwise
        return "ne" if _DEVANAGARI_RE.search(text) else "en"
    if _DEVANAGARI_RE.search(text):
        return "ne"
    return "en"


async def synthesize(text: str, http: httpx.AsyncClient, language: str = "ne") -> bytes:
    """Synthesize speech.  Returns raw WAV bytes or empty bytes on failure.

    Args:
        text:     The text to speak.  Should already have been through
                  finalize_reply() — this function applies only the lightweight
                  TTS-specific format cleanup on top.
        http:     Shared httpx.AsyncClient (from app.state).
        language: Language hint from the STT/hearing layer (e.g. "ne", "en",
                  "mixed").  Passed through to the ML service so it can route
                  to the right voice.
    """
    if not text.strip():
        return b""

    tts_language = _infer_tts_language(text, language)
    clean_text = clean_for_tts(text)
    if not clean_text.strip():
        return b""

    try:
        resp = await http.post(
            f"{settings.ml_service_url}/tts",
            json={"text": clean_text, "language": tts_language},
            timeout=settings.ml_timeout,
        )
        resp.raise_for_status()
        return resp.content  # WAV bytes
    except Exception as exc:
        logger.warning("TTS failed (%s) — returning empty audio", exc)
        return b""
