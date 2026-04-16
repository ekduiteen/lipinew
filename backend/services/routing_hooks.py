"""Future-safe routing hooks for adapters and voice/profile selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from services.behavior_policy import BehaviorPolicy
from services.input_understanding import InputUnderstanding
from services.teacher_modeling import TeacherModel


@dataclass(frozen=True)
class RoutingHooks:
    dialect_adapter: str | None
    behavior_adapter: str | None
    stt_bias: str | None
    tts_voice_profile: str | None
    response_ranker: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def build_routing_hooks(
    *,
    teacher_model: TeacherModel,
    understanding: InputUnderstanding,
    behavior_policy: BehaviorPolicy,
) -> RoutingHooks:
    dialect_adapter = teacher_model.dialect_signature_hook
    behavior_adapter = teacher_model.teaching_style
    stt_bias = understanding.dialect_guess
    tts_voice_profile = "english_piper" if behavior_policy.response_language == "en" else "nepali_piper"
    response_ranker = "correction_ranker" if understanding.is_correction else "default_ranker"
    return RoutingHooks(
        dialect_adapter=dialect_adapter,
        behavior_adapter=behavior_adapter,
        stt_bias=stt_bias,
        tts_voice_profile=tts_voice_profile,
        response_ranker=response_ranker,
    )
