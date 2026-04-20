"""Structured teacher-turn intent recognition."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re

from services.hearing import HearingResult
from services.keyterm_service import KeytermPreparation, normalize_term

_CORRECTION_PATTERNS = (
    "होइन",
    "यसरी भनिन्छ",
    "not like that",
    "correct is",
    "instead say",
    "say it like",
)
_TEACHING_PATTERNS = (
    "भनेको",
    "means",
    "how do you say",
    "लाई",
    "is called",
    "means this",
)
_CLARIFICATION_PATTERNS = (
    "i mean",
    "मेरो मतलब",
    "भन्न खोजेको",
    "in other words",
)
_CONFIRMATION_PATTERNS = (
    "हो",
    "ठीक छ",
    "yes",
    "right",
    "correct",
)
_EXAMPLE_PATTERNS = (
    "उदाहरण",
    "example",
    "sentence",
    "वाक्य",
)
_PRONUNCIATION_PATTERNS = (
    "उच्चारण",
    "pronounce",
    "pronunciation",
    "sound like",
)
_REGISTER_PATTERNS = (
    "तिमी भनेर बोल",
    "तपाईं भनेर बोल",
    "हजुर भन्नुहोस्",
    "use timi",
    "use tapai",
    "formal",
    "informal",
    "respectful",
)
_CODE_SWITCH_PATTERNS = (
    "in newari",
    "in maithili",
    "in english",
    "means in",
    "नेपाल भाषामा",
    "नेवारीमा",
)


@dataclass(frozen=True)
class IntentResult:
    label: str
    confidence: float
    secondary_labels: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def classify_intent(
    *,
    hearing: HearingResult,
    repaired_text: str,
    keyterms: KeytermPreparation,
    memory_context: dict | None = None,
) -> IntentResult:
    memory_context = memory_context or {}
    text = repaired_text.strip()
    lowered = text.lower()
    evidence: list[str] = []
    scores = {
        "correction": 0.0,
        "teaching": 0.0,
        "clarification": 0.0,
        "confirmation": 0.0,
        "example": 0.0,
        "pronunciation_guidance": 0.0,
        "register_instruction": 0.0,
        "code_switch_explanation": 0.0,
        "casual_chat": 0.0,
        "low_signal": 0.0,
    }

    if hearing.confidence < 0.58 or len(text) < 4:
        scores["low_signal"] += 0.85
        evidence.append("low_confidence_or_short")

    if _has_any(lowered, _CORRECTION_PATTERNS):
        scores["correction"] += 0.92
        evidence.append("correction_phrase")
    if _has_any(lowered, _TEACHING_PATTERNS):
        scores["teaching"] += 0.72
        evidence.append("teaching_phrase")
    if _has_any(lowered, _CLARIFICATION_PATTERNS):
        scores["clarification"] += 0.7
        evidence.append("clarification_phrase")
    if _has_any(lowered, _CONFIRMATION_PATTERNS) and len(text.split()) <= 4:
        scores["confirmation"] += 0.68
        evidence.append("short_confirmation")
    if _has_any(lowered, _EXAMPLE_PATTERNS):
        scores["example"] += 0.78
        evidence.append("example_phrase")
    if _has_any(lowered, _PRONUNCIATION_PATTERNS):
        scores["pronunciation_guidance"] += 0.88
        evidence.append("pronunciation_phrase")
    if _has_any(lowered, _REGISTER_PATTERNS):
        scores["register_instruction"] += 0.9
        evidence.append("register_phrase")
    if _has_any(lowered, _CODE_SWITCH_PATTERNS):
        scores["code_switch_explanation"] += 0.82
        evidence.append("code_switch_phrase")

    if hearing.mode == "mixed":
        scores["code_switch_explanation"] += 0.08
    if normalize_term(text) == normalize_term(str(memory_context.get("last_correction") or "")):
        scores["correction"] += 0.06
    if keyterms.matched_from_session:
        scores["teaching"] += 0.03
    if "?" in text and not scores["correction"]:
        scores["clarification"] += 0.08
    if len(text.split()) >= 7 and not any(scores[label] >= 0.6 for label in ("correction", "teaching", "example", "pronunciation_guidance")):
        scores["casual_chat"] += 0.48
        evidence.append("long_social_turn")
    elif len(text.split()) >= 4 and hearing.conversation_allowed:
        scores["casual_chat"] += 0.2

    if hearing.quality_label == "medium":
        scores["low_signal"] += 0.2
    if hearing.mode == "english" and not any(scores[label] >= 0.6 for label in ("teaching", "clarification", "code_switch_explanation")):
        scores["casual_chat"] += 0.2

    label, confidence = max(scores.items(), key=lambda item: item[1])
    if confidence < 0.45:
        label = "low_signal"
        confidence = max(confidence, 0.45 if hearing.conversation_allowed else 0.8)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    secondary_labels = [name for name, score in ranked[1:4] if score >= 0.45 and name != label]
    confidence = max(0.0, min(confidence, 0.99))
    return IntentResult(
        label=label,
        confidence=round(confidence, 3),
        secondary_labels=secondary_labels,
        evidence=evidence,
    )
