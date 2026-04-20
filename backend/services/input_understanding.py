"""Input understanding: unify hearing, turn interpretation, and optional audio-sidecar signals."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from services.audio_understanding import AudioUnderstandingResult
from services.hearing import HearingResult
from services.turn_interpreter import TurnInterpretation


@dataclass(frozen=True)
class InputUnderstanding:
    turn_id: str
    intent_label: str
    intent_confidence: float
    secondary_intents: list[str]
    primary_language: str
    secondary_languages: list[str]
    code_switch_ratio: float
    topic: str
    tone: str
    emotion: str
    is_correction: bool
    is_teaching: bool
    taught_terms: list[str]
    register_estimate: str
    dialect_guess: str | None
    dialect_confidence: float
    speech_rate: str
    prosody_pattern: str
    pronunciation_style: str
    transcript_confidence: float
    learning_allowed: bool
    conversation_allowed: bool
    usable_for_learning: bool
    unusable_reason: str | None
    learning_weight: float
    signal_confidences: dict[str, float]

    def to_dict(self) -> dict:
        return asdict(self)


def _fallback_audio_signals(
    hearing: HearingResult,
    interpretation: TurnInterpretation,
) -> AudioUnderstandingResult:
    secondary_languages: list[str] = []
    code_switch_ratio = 0.0
    if hearing.mode == "mixed":
        secondary_languages = ["en"]
        code_switch_ratio = 0.35
    elif hearing.mode == "english":
        secondary_languages = []
        code_switch_ratio = 0.0

    lowered = hearing.clean_text.lower()
    dialect_guess = None
    dialect_confidence = 0.0
    pronunciation_style = "standard_spoken"
    if "newari" in lowered or "newa" in lowered or "newari" in lowered or "jojolopa" in lowered:
        dialect_guess = "newari_kathmandu_mix"
        dialect_confidence = 0.72
        pronunciation_style = "newari_leaning"
    elif "kathmandu" in lowered:
        dialect_guess = "kathmandu"
        dialect_confidence = 0.6

    if hearing.mode == "english":
        register_estimate = "neutral"
    else:
        register_estimate = interpretation.register_hint or "timi"

    speech_rate = "medium"
    token_count = len(hearing.clean_text.split())
    duration_ms = int(hearing.audio_duration_ms or 0)
    if duration_ms > 0:
        words_per_second = token_count / max(duration_ms / 1000, 0.1)
        if words_per_second >= 2.8:
            speech_rate = "fast"
        elif words_per_second <= 1.3:
            speech_rate = "slow"
    elif token_count >= 8:
        speech_rate = "fast"

    tone = "friendly"
    emotion = interpretation.emotion_hint or "neutral"
    if interpretation.is_correction:
        tone = "helpful_formal"
    elif interpretation.intent_type == "chat_socially":
        tone = "friendly"

    primary_language = hearing.language or "ne"
    if dialect_guess and primary_language in {"en", "unknown"}:
        primary_language = "new"

    return AudioUnderstandingResult(
        primary_language=primary_language,
        secondary_languages=secondary_languages,
        code_switch_ratio=code_switch_ratio,
        tone=tone,
        emotion=emotion,
        is_correction=interpretation.is_correction,
        is_teaching=interpretation.intent_type in {"teach_word", "give_example", "regional_variation"},
        topic=interpretation.active_topic,
        dialect_guess=dialect_guess,
        dialect_confidence=dialect_confidence,
        speech_rate=speech_rate,
        prosody_pattern="rising" if interpretation.intent_type == "ask_question" else "neutral",
        pronunciation_style=pronunciation_style,
        register_estimate=register_estimate,
        model_source="text_heuristic_fallback",
        model_confidence=max(0.45, min(hearing.confidence, 0.78)),
    )


def merge_signals(
    turn_id: str,
    hearing: HearingResult,
    interpretation: TurnInterpretation,
    audio_signals: AudioUnderstandingResult,
    intent_label: str | None = None,
    intent_confidence: float | None = None,
    secondary_intents: list[str] | None = None,
    usable_for_learning: bool | None = None,
    unusable_reason: str | None = None,
    learning_weight: float | None = None,
    memory_context: dict | None = None,
) -> InputUnderstanding:
    """Merge Whisper/hearing, turn interpretation, and optional audio-sidecar signals."""

    del memory_context

    normalized_intent = str(intent_label or "").strip().lower()
    is_correction = bool(audio_signals.is_correction or interpretation.is_correction or normalized_intent == "correction")
    is_teaching = bool(
        audio_signals.is_teaching
        or interpretation.intent_type in {"teach_word", "give_example", "regional_variation"}
        or normalized_intent in {"teaching", "example", "pronunciation_guidance", "register_instruction", "code_switch_explanation"}
    )
    primary_lang = audio_signals.primary_language or hearing.language or "ne"
    topic = (
        audio_signals.topic
        if audio_signals.model_confidence > 0.5 and audio_signals.topic
        else interpretation.active_topic
    )
    signal_confidences = {
        "stt": hearing.confidence,
        "audio_model": audio_signals.model_confidence,
        "dialect": audio_signals.dialect_confidence,
    }

    return InputUnderstanding(
        turn_id=turn_id,
        intent_label=intent_label or interpretation.intent_type,
        intent_confidence=float(intent_confidence or max(audio_signals.model_confidence, hearing.confidence)),
        secondary_intents=list(secondary_intents or []),
        primary_language=primary_lang,
        secondary_languages=audio_signals.secondary_languages or [],
        code_switch_ratio=float(audio_signals.code_switch_ratio or 0.0),
        topic=topic or "everyday_basics",
        tone=audio_signals.tone or "neutral",
        emotion=audio_signals.emotion or interpretation.emotion_hint or "neutral",
        is_correction=is_correction,
        is_teaching=is_teaching,
        taught_terms=interpretation.taught_terms,
        register_estimate=audio_signals.register_estimate or interpretation.register_hint,
        dialect_guess=audio_signals.dialect_guess,
        dialect_confidence=float(audio_signals.dialect_confidence or 0.0),
        speech_rate=audio_signals.speech_rate or "medium",
        prosody_pattern=audio_signals.prosody_pattern or "neutral",
        pronunciation_style=audio_signals.pronunciation_style or "standard_spoken",
        transcript_confidence=float(hearing.confidence),
        learning_allowed=hearing.learning_allowed,
        conversation_allowed=hearing.conversation_allowed,
        usable_for_learning=hearing.learning_allowed if usable_for_learning is None else usable_for_learning,
        unusable_reason=unusable_reason,
        learning_weight=float(learning_weight or (0.75 if hearing.learning_allowed else 0.25)),
        signal_confidences=signal_confidences,
    )


def analyze_input(hearing: HearingResult, interpretation: TurnInterpretation) -> InputUnderstanding:
    """Backward-compatible text-first understanding path used by older services and tests."""
    audio_signals = _fallback_audio_signals(hearing, interpretation)
    return merge_signals(
        turn_id="legacy-analyze-input",
        hearing=hearing,
        interpretation=interpretation,
        audio_signals=audio_signals,
        memory_context=None,
    )
