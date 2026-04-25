"""
STT service client — calls ml:5001/stt (faster-whisper).
Groq Whisper fires only on local failure.
"""

from __future__ import annotations

import logging
import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings
from services.asr_drift import detect_asr_drift
from services.country_registry import get_base_asr_languages
from services.language_registry import is_adapter_available, load_language_profile

logger = logging.getLogger("lipi.backend.stt")


async def _local_transcribe(
    audio_bytes: bytes,
    http: httpx.AsyncClient,
    *,
    prompt: str | None = None,
    language_hint: str | None = None,
    candidate_languages: list[str] | None = None,
    base_asr_languages: list[str] | None = None,
    target_language: str | None = None,
    enable_auto_candidate: bool = True,
) -> dict:
    resp = await http.post(
        f"{settings.ml_service_url}/stt",
        files={"audio": ("audio.webm", audio_bytes, "audio/webm")},
        data={
            "prompt": prompt or "",
            "language_hint": language_hint or "",
            "candidate_languages_json": ",".join(candidate_languages or []),
            "base_asr_languages_json": ",".join(base_asr_languages or []),
            "target_language": target_language or "",
            "enable_auto_candidate": str(enable_auto_candidate).lower(),
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
    session_language_contract: dict | None = None,
    teacher_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    """Transcribe audio with country-anchored ASR routing."""
    del teacher_id, session_id

    contract = dict(session_language_contract or {})
    country_code = str(contract.get("country_code") or "NP")
    target_language = str(contract.get("target_language") or "").lower() or None
    region = str(contract.get("dialect_label") or "").strip().lower() or None
    base_asr_languages = contract.get("base_asr_languages") or get_base_asr_languages(country_code, region=None)
    base_asr_languages = [str(item).lower() for item in base_asr_languages]
    if country_code.upper() == "NP" and not base_asr_languages:
        base_asr_languages = ["ne", "en"]

    candidate_languages = list(dict.fromkeys(base_asr_languages))
    if target_language and target_language not in candidate_languages and is_adapter_available(target_language):
        candidate_languages.append(target_language)

    try:
        stt_result = await _local_transcribe(
            audio_bytes,
            http,
            prompt=prompt,
            language_hint=language_hint or (base_asr_languages[0] if base_asr_languages else None),
            candidate_languages=candidate_languages,
            base_asr_languages=base_asr_languages,
            target_language=target_language,
            enable_auto_candidate=True,
        )
    except Exception as exc:
        if not settings.groq_api_key:
            logger.error("Local STT error with no Groq fallback configured: %s", exc)
            raise
        logger.warning("Local STT error (%s), activating Groq fallback", exc)
        stt_result = await _groq_transcribe(audio_bytes, http, prompt=prompt)

    selected_transcript = str(stt_result.get("selected_transcript") or stt_result.get("text") or "")
    candidates = [dict(item) for item in stt_result.get("candidates", [])]
    if not candidates and selected_transcript:
        selected_language = str(stt_result.get("selected_language") or stt_result.get("language") or "")
        candidates = [
            {
                "candidate_type": "fallback",
                "language_code": selected_language,
                "transcript": selected_transcript,
                "confidence": float(stt_result.get("confidence") or 0.0),
                "model_name": "groq-whisper-large-v3" if settings.groq_api_key else "unknown",
                "selected": True,
                "rank": 1,
            }
        ]

    if base_asr_languages and not any(c.get("candidate_type") == "base_nepali" for c in candidates):
        candidates.append(
            {
                "candidate_type": "base_nepali",
                "language_code": "ne",
                "transcript": "",
                "confidence": 0.0,
                "model_name": "placeholder",
                "selected": False,
                "rank": len(candidates) + 1,
            }
        )
    if "en" in base_asr_languages and not any(c.get("candidate_type") == "base_english" for c in candidates):
        candidates.append(
            {
                "candidate_type": "base_english",
                "language_code": "en",
                "transcript": "",
                "confidence": 0.0,
                "model_name": "placeholder",
                "selected": False,
                "rank": len(candidates) + 1,
            }
        )

    selected_language = str(stt_result.get("selected_language") or stt_result.get("language") or "")
    detected_language = str(stt_result.get("detected_language") or stt_result.get("language") or "")
    confidence = float(stt_result.get("confidence") or 0.0)
    code_switch_ratio = _estimate_code_switch_ratio(selected_transcript)
    drift = detect_asr_drift(
        target_language=target_language or "",
        selected_language=selected_language,
        detected_language=detected_language,
        base_asr_languages=base_asr_languages,
        confidence=confidence,
        code_switch_ratio=code_switch_ratio,
        candidates=candidates,
    )
    try:
        language_profile = load_language_profile(target_language or selected_language or "ne")
        thresholds = language_profile.get("quality_thresholds", {})
        low_confidence_threshold = float(thresholds.get("low_confidence", 0.55))
    except ValueError:
        low_confidence_threshold = 0.55

    stt_result.update(
        {
            "text": selected_transcript,
            "language": selected_language or detected_language,
            "selected_transcript": selected_transcript,
            "selected_language": selected_language or detected_language,
            "detected_language": detected_language,
            "target_language": target_language,
            "base_asr_languages": base_asr_languages,
            "needs_teacher_confirmation": bool(drift["needs_teacher_confirmation"] or confidence < low_confidence_threshold),
            "asr_drift_type": drift["asr_drift_type"],
            "asr_drift_reason": drift["reason"],
            "asr_drift_severity": drift["severity"],
            "code_switch_ratio": code_switch_ratio,
            "candidates": candidates,
        }
    )
    return stt_result


def _estimate_code_switch_ratio(text: str) -> float:
    stripped = str(text or "").strip()
    if not stripped:
        return 0.0
    devanagari = len(re.findall(r"[\u0900-\u097F]", stripped))
    latin = len(re.findall(r"[A-Za-z]", stripped))
    total = devanagari + latin
    if total == 0:
        return 0.0
    return min(devanagari, latin) / total
