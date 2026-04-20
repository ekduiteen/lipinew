"""Build structured training-data envelopes for each teacher turn."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from services.behavior_policy import BehaviorPolicy
from services.input_understanding import InputUnderstanding
from services.turn_intelligence import TurnIntelligence
from services.turn_interpreter import TurnInterpretation


def _signal(value, confidence: float, source: str) -> dict:
    return {
        "value": value,
        "confidence": round(max(0.0, min(float(confidence), 1.0)), 3),
        "source": source,
    }


@dataclass(frozen=True)
class TrainingCaptureEnvelope:
    raw_data: dict
    derived_signals: dict
    high_value_signals: dict
    style_signals: dict
    prosody_signals: dict
    nuance_signals: dict

    def to_dict(self) -> dict:
        return asdict(self)


def build_training_capture(
    *,
    session_id: str,
    teacher_id: str,
    transcript: str,
    stt_confidence: float,
    audio_path: str | None,
    audio_duration_ms: int | None,
    speaker_embedding: list[float] | None,
    understanding: InputUnderstanding,
    interpretation: TurnInterpretation,
    behavior_policy: BehaviorPolicy,
    correction_event_id: str | None = None,
    taught_words: list[str] | None = None,
    usage_rules: list[str] | None = None,
    cultural_notes: list[str] | None = None,
    turn_intelligence: TurnIntelligence | None = None,
) -> TrainingCaptureEnvelope:
    timestamp = datetime.now(timezone.utc).isoformat()
    source = "input_understanding_v1"

    raw_data = {
        "session_id": session_id,
        "teacher_id": teacher_id,
        "audio_path": audio_path,
        "transcript": transcript,
        "stt_confidence": stt_confidence,
        "audio_duration_ms": audio_duration_ms,
        "timestamp": timestamp,
        "speaker_embedding": _signal(speaker_embedding or [], 0.0 if not speaker_embedding else 0.4, "speaker_embedding_hook_pending"),
    }

    derived_signals = {
        "intent_label": _signal(
            turn_intelligence.intent.label if turn_intelligence else understanding.intent_label,
            turn_intelligence.intent.confidence if turn_intelligence else understanding.intent_confidence,
            "turn_intelligence_v1" if turn_intelligence else source,
        ),
        "secondary_intents": _signal(
            turn_intelligence.intent.secondary_labels if turn_intelligence else understanding.secondary_intents,
            0.6,
            "turn_intelligence_v1" if turn_intelligence else source,
        ),
        "primary_language": _signal(understanding.primary_language, 0.85, source),
        "secondary_languages": _signal(understanding.secondary_languages, 0.65, source),
        "code_switch_ratio": _signal(understanding.code_switch_ratio, 0.7, source),
        "topic": _signal(understanding.topic, 0.72, "turn_interpreter_v1"),
        "tone": _signal(understanding.tone, 0.7, source),
        "register": _signal(understanding.register_estimate, 0.72, "turn_interpreter_v1"),
        "dialect_guess": _signal(understanding.dialect_guess, understanding.dialect_confidence, source),
        "dialect_confidence": _signal(understanding.dialect_confidence, understanding.dialect_confidence, source),
        "speech_rate": _signal(understanding.speech_rate, 0.55, source),
        "prosody": _signal(understanding.prosody_pattern, 0.5, source),
        "emotion": _signal(interpretation.emotion_hint, 0.55 if interpretation.emotion_hint else 0.0, "turn_interpreter_v1"),
        "pronunciation_style": _signal(understanding.pronunciation_style, 0.55, source),
        "code_switch_analysis": _signal(
            turn_intelligence.code_switch.to_dict() if turn_intelligence else {},
            0.75 if turn_intelligence else 0.0,
            "turn_intelligence_v1" if turn_intelligence else source,
        ),
    }

    high_value_signals = {
        "is_correction": _signal(understanding.is_correction, 0.9 if understanding.is_correction else 0.7, "turn_interpreter_v1"),
        "turn_intelligence": _signal(
            turn_intelligence.to_dict() if turn_intelligence else {},
            0.82 if turn_intelligence else 0.0,
            "turn_intelligence_v1" if turn_intelligence else source,
        ),
        "correction_event_id": _signal(correction_event_id, 1.0 if correction_event_id else 0.0, "correction_graph_v1"),
        "taught_words": _signal(taught_words or interpretation.taught_terms, 0.8 if (taught_words or interpretation.taught_terms) else 0.2, "turn_interpreter_v1"),
        "usage_rules": _signal(usage_rules or [], 0.0 if not usage_rules else 0.75, "learning_worker_v1"),
        "cultural_notes": _signal(cultural_notes or [], 0.0 if not cultural_notes else 0.6, "learning_worker_v1"),
        "teacher_id": _signal(teacher_id, 1.0, "session_context"),
        "behavior_policy": _signal(behavior_policy.to_dict(), 0.8, "behavior_policy_v1"),
    }

    style_signals = {
        "tone_style": _signal(behavior_policy.tone_style, 0.8, "behavior_policy_v1"),
        "register_estimate": _signal(understanding.register_estimate, 0.72, "turn_interpreter_v1"),
        "politeness_level": _signal(behavior_policy.politeness_level, 0.78, "behavior_policy_v1"),
        "mirror_code_switching": _signal(behavior_policy.mirror_code_switching, 0.82, "behavior_policy_v1"),
    }

    prosody_signals = {
        "speech_rate": _signal(understanding.speech_rate, 0.55, source),
        "prosody_pattern": _signal(understanding.prosody_pattern, 0.5, source),
        "audio_quality_score": _signal(getattr(understanding, "transcript_confidence", 0.0), 0.6, "hearing_v1"),
        "transcript_repair": _signal(
            turn_intelligence.transcript_repair.to_dict() if turn_intelligence else {},
            0.7 if turn_intelligence and turn_intelligence.transcript_repair.applied_repairs else 0.0,
            "turn_intelligence_v1" if turn_intelligence else source,
        ),
    }

    nuance_signals = {
        "dialect_guess": _signal(understanding.dialect_guess, understanding.dialect_confidence, source),
        "pronunciation_style": _signal(understanding.pronunciation_style, 0.55, source),
        "tone": _signal(understanding.tone, 0.7, source),
        "topic": _signal(understanding.topic, 0.72, "turn_interpreter_v1"),
        "response_language": _signal(behavior_policy.response_language, 0.85, "behavior_policy_v1"),
        "learning_weight": _signal(
            turn_intelligence.learning_weight if turn_intelligence else understanding.learning_weight,
            0.8,
            "turn_intelligence_v1" if turn_intelligence else source,
        ),
    }

    return TrainingCaptureEnvelope(
        raw_data=raw_data,
        derived_signals=derived_signals,
        high_value_signals=high_value_signals,
        style_signals=style_signals,
        prosody_signals=prosody_signals,
        nuance_signals=nuance_signals,
    )
