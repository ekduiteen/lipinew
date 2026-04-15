"""Structured input understanding built on top of hearing + turn interpretation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from services.hearing import HearingResult
from services.turn_interpreter import TurnInterpretation


_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_HELPFUL_HINTS = ("please", "let me", "i'll tell", "सिकाउँछु", "बताउँछु", "भनिदिन्छु")
_FORMAL_HINTS = ("तपाईं", "हजुर", "please", "sir", "madam")
_CASUAL_HINTS = ("तिमी", "तँ", "buddy", "bro", "haha", "lol")
_GREETING_HINTS = ("hello", "hi", "namaste", "नमस्ते", "jojolopa", "जोजोलोपा")


@dataclass(frozen=True)
class InputUnderstanding:
    primary_language: str
    secondary_languages: list[str]
    code_switch_ratio: float
    is_correction: bool
    is_teaching: bool
    topic: str
    tone: str
    transcript_confidence: float
    quality_label: str
    conversation_allowed: bool
    learning_allowed: bool
    dialect_hook: str | None
    dialect_guess: str | None
    dialect_confidence: float
    speech_rate: str
    pronunciation_style: str
    prosody_pattern: str
    register_estimate: str
    reason_codes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _infer_secondary_languages(text: str, primary_language: str) -> list[str]:
    secondary: list[str] = []
    if _LATIN_RE.search(text) and primary_language != "en":
        secondary.append("en")
    lowered = text.lower()
    if any(marker in lowered for marker in ("newari", "nepal bhasa", "newa")) and primary_language != "new":
        secondary.append("new")
    return secondary


def _estimate_code_switch_ratio(text: str) -> float:
    lowered = text.lower()
    local_language_hints = ("newari", "nepal bhasa", "newa", "jojolopa", "bhancha", "ma")
    has_local_hint = any(token in lowered for token in local_language_hints)
    has_english_hint = any(ch.isascii() and ch.isalpha() for ch in text)

    latin_count = len(_LATIN_RE.findall(text))
    devanagari_count = len(_DEVANAGARI_RE.findall(text))
    total = latin_count + devanagari_count
    if total == 0:
        return 0.35 if has_local_hint and has_english_hint else 0.0
    if devanagari_count == 0 and has_local_hint and has_english_hint:
        return 0.35
    return round(min(latin_count, devanagari_count) / total, 3)


def _infer_tone(text: str, interpretation: TurnInterpretation) -> str:
    lowered = text.lower()
    helpful = any(token in lowered for token in _HELPFUL_HINTS) or interpretation.is_correction
    formal = interpretation.register_hint in {"tapai", "hajur"} or any(token in text for token in _FORMAL_HINTS)
    casual = interpretation.register_hint in {"timi", "ta"} or any(token in lowered for token in _CASUAL_HINTS)

    if helpful and formal:
        return "helpful_formal"
    if helpful and casual:
        return "helpful_casual"
    if formal:
        return "formal"
    if casual:
        return "casual"
    return "neutral"


def _normalize_topic(text: str, interpretation: TurnInterpretation) -> str:
    lowered = text.lower()
    if any(token in lowered for token in _GREETING_HINTS):
        return "greeting_usage"
    if interpretation.active_topic:
        return interpretation.active_topic
    return "everyday_basics"


def _estimate_speech_rate(text: str, duration_ms: int | None) -> str:
    if not duration_ms or duration_ms <= 0:
        return "unknown"
    words = max(len(text.split()), 1)
    words_per_second = words / max(duration_ms / 1000, 0.25)
    if words_per_second < 1.6:
        return "slow"
    if words_per_second > 3.2:
        return "fast"
    return "medium"


def _estimate_pronunciation_style(text: str, primary_language: str, code_switch_ratio: float) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("newari", "newa", "nepal bhasa", "jojolopa")):
        return "newari_leaning"
    if primary_language == "en" and code_switch_ratio < 0.15:
        return "english_forward"
    if code_switch_ratio >= 0.28:
        return "code_switched"
    return "standard_spoken"


def _estimate_prosody_pattern(text: str, tone: str, speech_rate: str) -> str:
    if "?" in text:
        return "question_rise"
    if tone.startswith("helpful"):
        return "guided_even"
    if speech_rate == "fast":
        return "compressed"
    if speech_rate == "slow":
        return "measured"
    return "neutral"


def _guess_dialect(
    text: str,
    primary_language: str,
    secondary_languages: list[str],
    code_switch_ratio: float,
) -> tuple[str | None, float]:
    lowered = text.lower()
    if any(token in lowered for token in ("newari", "newa", "nepal bhasa", "jojolopa")):
        return "newari_kathmandu_mix", 0.68
    if primary_language == "ne" and "en" in secondary_languages and code_switch_ratio >= 0.25:
        return "kathmandu_mix", 0.58
    if any(token in lowered for token in ("maithili", "bhojpuri", "tharu", "tamang")):
        return "regional_named_variant", 0.64
    return None, 0.0


def analyze_input(
    hearing: HearingResult,
    interpretation: TurnInterpretation,
) -> InputUnderstanding:
    primary_language = "new" if any(
        token in hearing.clean_text.lower() for token in ("newari", "nepal bhasa", "newa")
    ) else hearing.language
    secondary_languages = _infer_secondary_languages(hearing.clean_text, primary_language)
    code_switch_ratio = _estimate_code_switch_ratio(hearing.clean_text)
    if hearing.mode == "mixed" and code_switch_ratio == 0.0:
        code_switch_ratio = 0.35
    tone = _infer_tone(hearing.clean_text, interpretation)
    topic = _normalize_topic(hearing.clean_text, interpretation)
    speech_rate = _estimate_speech_rate(hearing.clean_text, hearing.audio_duration_ms)
    pronunciation_style = _estimate_pronunciation_style(
        hearing.clean_text,
        primary_language,
        code_switch_ratio,
    )
    prosody_pattern = _estimate_prosody_pattern(hearing.clean_text, tone, speech_rate)
    dialect_guess, dialect_confidence = _guess_dialect(
        hearing.clean_text,
        primary_language,
        secondary_languages,
        code_switch_ratio,
    )

    dialect_hook = None
    lowered = hearing.clean_text.lower()
    if any(token in lowered for token in ("newari", "nepal bhasa", "newa")):
        dialect_hook = "newari_bias"
    elif any(token in lowered for token in ("maithili", "bhojpuri", "tharu", "tamang")):
        dialect_hook = "regional_language_bias"

    return InputUnderstanding(
        primary_language=primary_language or "unknown",
        secondary_languages=secondary_languages,
        code_switch_ratio=code_switch_ratio,
        is_correction=interpretation.is_correction,
        is_teaching=interpretation.intent_type in {"teach_word", "give_example", "invite_lipi_choice"},
        topic=topic,
        tone=tone,
        transcript_confidence=hearing.confidence,
        quality_label=hearing.quality_label,
        conversation_allowed=hearing.conversation_allowed,
        learning_allowed=hearing.learning_allowed,
        dialect_hook=dialect_hook,
        dialect_guess=dialect_guess,
        dialect_confidence=dialect_confidence,
        speech_rate=speech_rate,
        pronunciation_style=pronunciation_style,
        prosody_pattern=prosody_pattern,
        register_estimate=interpretation.register_hint,
        reason_codes=hearing.reason_codes,
    )
