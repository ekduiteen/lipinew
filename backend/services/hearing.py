"""Hearing engine: convert STT output into a trusted interaction signal."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re


_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_NOISE_MARKERS = ("uh", "umm", "mm", "noise", "[noise]", "[inaudible]")


@dataclass(frozen=True)
class HearingResult:
    raw_text: str
    clean_text: str
    confidence: float
    language: str
    mode: str
    quality_label: str
    audio_quality_score: float
    audio_duration_ms: int | None
    conversation_allowed: bool
    learning_allowed: bool
    reason_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _detect_mode(text: str, language: str) -> str:
    devanagari_count = len(_DEVANAGARI_RE.findall(text))
    latin_count = len(_LATIN_RE.findall(text))

    if language == "en" or (latin_count > max(8, devanagari_count * 2)):
        return "english"
    if latin_count > 0 and devanagari_count > 0:
        return "mixed"
    return "nepali"


def analyze_hearing(stt_result: dict) -> HearingResult:
    raw_text = str(stt_result.get("text") or "")
    clean_text = " ".join(raw_text.strip().split())
    confidence = float(stt_result.get("confidence") or 0.0)
    language = str(stt_result.get("language") or "unknown").lower()
    audio_duration_ms = int(stt_result.get("duration_ms") or 0) or None
    mode = _detect_mode(clean_text, language)

    reason_codes: list[str] = []

    if not clean_text:
        reason_codes.append("empty_text")
    if len(clean_text) < 3:
        reason_codes.append("too_short")
    if any(marker in clean_text.lower() for marker in _NOISE_MARKERS):
        reason_codes.append("noise_marker")

    if confidence < 0.56:
        quality_label = "low"
        conversation_allowed = False
        learning_allowed = False
        reason_codes.append("low_confidence")
    elif confidence < 0.74:
        quality_label = "medium"
        conversation_allowed = True
        learning_allowed = False
        reason_codes.append("medium_confidence")
    else:
        quality_label = "good"
        conversation_allowed = True
        learning_allowed = True

    if mode == "mixed":
        reason_codes.append("code_switched")
    if mode == "english":
        reason_codes.append("english_mode")

    if "empty_text" in reason_codes or "too_short" in reason_codes:
        conversation_allowed = False
        learning_allowed = False

    audio_quality_score = confidence
    if "noise_marker" in reason_codes:
        audio_quality_score -= 0.15
    if "too_short" in reason_codes:
        audio_quality_score -= 0.1
    audio_quality_score = max(0.0, min(round(audio_quality_score, 3), 1.0))

    return HearingResult(
        raw_text=raw_text,
        clean_text=clean_text,
        confidence=confidence,
        language=language,
        mode=mode,
        quality_label=quality_label,
        audio_quality_score=audio_quality_score,
        audio_duration_ms=audio_duration_ms,
        conversation_allowed=conversation_allowed,
        learning_allowed=learning_allowed,
        reason_codes=reason_codes,
    )
