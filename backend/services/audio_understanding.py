"""Audio Understanding Abstraction Layer

Provides a safe hybrid-mode extraction of acoustic features, dialect signals, 
and intent from raw audio. Downgrades gracefully on failure so the live path 
(Whisper + LLM text generation) is never blocked.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
import httpx

from config import settings

logger = logging.getLogger("lipi.backend.audio_understanding")


@dataclass(frozen=True)
class AudioUnderstandingResult:
    primary_language: str
    secondary_languages: list[str]
    code_switch_ratio: float
    tone: str
    emotion: str
    is_correction: bool
    is_teaching: bool
    topic: str
    dialect_guess: str | None
    dialect_confidence: float
    speech_rate: str
    prosody_pattern: str
    pronunciation_style: str
    register_estimate: str
    model_source: str
    model_confidence: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def fallback(cls, transcript: str | None = None) -> AudioUnderstandingResult:
        """Safe fallback to avoid blocking the synchronous pipeline if external multimodal API fails."""
        # We can implement basic heuristics here based on transcript if needed,
        # but the point is to gracefully degrade.
        return cls(
            primary_language="ne",
            secondary_languages=[],
            code_switch_ratio=0.0,
            tone="neutral",
            emotion="neutral",
            is_correction=False,   # Let input_understanding via Whisper text catch it
            is_teaching=False,
            topic="everyday_basics",
            dialect_guess=None,
            dialect_confidence=0.0,
            speech_rate="medium",
            prosody_pattern="neutral",
            pronunciation_style="standard_spoken",
            register_estimate="neutral",
            model_source="fallback",
            model_confidence=0.0
        )


async def extract_audio_signals(
    *,
    http: httpx.AsyncClient,
    audio_uri: str | None = None,
    audio_bytes: bytes | None = None,
    rough_transcript: str | None = None,
    metadata: dict | None = None,
) -> AudioUnderstandingResult:
    """Extract acoustic signals using an external API, falling back gracefully on failure."""
    if not audio_uri and not audio_bytes:
        logger.warning("No audio provided to audio_understanding. Falling back to text heuristics.")
        return AudioUnderstandingResult.fallback(rough_transcript)

    # Note: In a production environment with Gemma 4 / 3n available natively via Vertex AI or AI Studio,
    # we would format this API call properly to the multimodal endpoint endpoint. 
    # For MVP safety, we abstract this with a short timeout to prevent WS blocking.
    
    payload = {
        "audio_uri": audio_uri,
        "transcript": rough_transcript,
        "metadata": metadata or {}
    }
    
    try:
        response = await http.post(
            f"{settings.ml_service_url}/audio-understand",  # Hypothetical internal router
            json=payload,
            timeout=1.5  # Critical: short timeout to protect latency
        )
        response.raise_for_status()
        data = response.json()
        
        return AudioUnderstandingResult(
            primary_language=data.get("primary_language", "ne"),
            secondary_languages=data.get("secondary_languages", []),
            code_switch_ratio=float(data.get("code_switch_ratio", 0.0)),
            tone=data.get("tone", "neutral"),
            emotion=data.get("emotion", "neutral"),
            is_correction=bool(data.get("is_correction", False)),
            is_teaching=bool(data.get("is_teaching", False)),
            topic=data.get("topic", "everyday_basics"),
            dialect_guess=data.get("dialect_guess"),
            dialect_confidence=float(data.get("dialect_confidence", 0.0)),
            speech_rate=data.get("speech_rate", "medium"),
            prosody_pattern=data.get("prosody_pattern", "neutral"),
            pronunciation_style=data.get("pronunciation_style", "standard_spoken"),
            register_estimate=data.get("register_estimate", "neutral"),
            model_source=data.get("model_source", "gemma_audio_v1"),
            model_confidence=float(data.get("model_confidence", 0.5))
        )
    except (httpx.RequestError, httpx.HTTPStatusError, httpx.TimeoutException, ValueError) as exc:
        logger.warning(f"Audio understanding failed: {exc}. Falling back cleanly.")
        return AudioUnderstandingResult.fallback(rough_transcript)
