"""Behavior policy engine: decide how LIPI should behave on this turn."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from services.input_understanding import InputUnderstanding
from services.memory_service import StructuredSessionMemory
from services.teacher_modeling import TeacherModel


@dataclass(frozen=True)
class BehaviorPolicy:
    response_language: str
    mirror_code_switching: bool
    register: str
    tone_style: str
    uncertainty_level: float
    curiosity_level: float
    confirmation_style: str
    max_followups: int
    allowed_humor: float
    infer_vs_ask: str
    dialect_alignment: str
    politeness_level: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_prompt_block(self) -> str:
        return (
            "## Behavior policy\n"
            f"- Response language: {self.response_language}\n"
            f"- Mirror code switching: {str(self.mirror_code_switching).lower()}\n"
            f"- Register: {self.register}\n"
            f"- Tone style: {self.tone_style}\n"
            f"- Uncertainty level: {self.uncertainty_level:.2f}\n"
            f"- Curiosity level: {self.curiosity_level:.2f}\n"
            f"- Confirmation style: {self.confirmation_style}\n"
            f"- Max follow-ups: {self.max_followups}\n"
            f"- Allowed humor: {self.allowed_humor:.2f}\n"
            f"- Infer vs ask: {self.infer_vs_ask}\n"
            f"- Dialect alignment: {self.dialect_alignment}\n"
            f"- Politeness level: {self.politeness_level}\n"
        )


def choose_behavior_policy(
    *,
    teacher_model: TeacherModel,
    session_memory: StructuredSessionMemory,
    correction_count_recent: int,
    understanding: InputUnderstanding,
) -> BehaviorPolicy:
    if understanding.primary_language == "en":
        response_language = "en"
    elif understanding.primary_language in {"new", "newari"}:
        response_language = "ne"
    else:
        response_language = understanding.primary_language or "ne"

    mirror_code_switching = understanding.code_switch_ratio >= 0.28 and teacher_model.teaching_style != "formal_guided"
    uncertainty_level = max(0.05, min(1.0, 1.0 - understanding.transcript_confidence))
    if not understanding.conversation_allowed:
        uncertainty_level = max(uncertainty_level, 0.85)

    curiosity_level = 0.7
    if understanding.is_teaching:
        curiosity_level += 0.1
    if understanding.topic in {"regional_variation", "culture_ritual", "greeting_usage"}:
        curiosity_level += 0.1
    if correction_count_recent >= 2:
        curiosity_level -= 0.1
    curiosity_level = max(0.35, min(curiosity_level, 0.95))

    if not understanding.conversation_allowed:
        confirmation_style = "ask_repeat"
        infer_vs_ask = "ask"
    elif understanding.transcript_confidence < 0.74:
        confirmation_style = "inference_first"
        infer_vs_ask = "ask"
    elif understanding.is_correction:
        confirmation_style = "correction_accept"
        infer_vs_ask = "infer"
    else:
        confirmation_style = "light_ack"
        infer_vs_ask = "infer"

    allowed_humor = 0.05
    if teacher_model.preferred_register in {"timi", "ta"} and teacher_model.teaching_style in {"steady_teacher", "multilingual_bridge"}:
        allowed_humor = 0.15
    if teacher_model.preferred_register in {"tapai", "hajur"}:
        allowed_humor = min(allowed_humor, 0.05)

    if session_memory.unresolved_misunderstandings:
        infer_vs_ask = "ask"
        confirmation_style = "repair"

    if teacher_model.preferred_register in {"hajur", "tapai"}:
        politeness_level = "high"
    elif teacher_model.preferred_register == "timi":
        politeness_level = "medium"
    else:
        politeness_level = "low"

    tone_style = understanding.tone
    if understanding.is_correction:
        tone_style = "respectful_accepting"
    elif understanding.is_teaching:
        tone_style = "curious_warm"

    dialect_alignment = understanding.dialect_guess or teacher_model.dialect_signature_hook or "neutral"

    return BehaviorPolicy(
        response_language=response_language,
        mirror_code_switching=mirror_code_switching,
        register=teacher_model.preferred_register,
        tone_style=tone_style,
        uncertainty_level=round(uncertainty_level, 3),
        curiosity_level=round(curiosity_level, 3),
        confirmation_style=confirmation_style,
        max_followups=1,
        allowed_humor=round(allowed_humor, 3),
        infer_vs_ask=infer_vs_ask,
        dialect_alignment=dialect_alignment,
        politeness_level=politeness_level,
    )
