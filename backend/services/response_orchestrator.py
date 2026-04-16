"""Centralized response assembly for the live LIPI turn."""

from __future__ import annotations

from dataclasses import dataclass

from services.behavior_policy import BehaviorPolicy
from services.curriculum import QuestionPlan
from services.input_understanding import InputUnderstanding
from services.memory_service import StructuredSessionMemory, build_memory_summary
from services.personality import ResponsePlan
from services.prompt_builder import TeacherProfile, build_turn_guidance
from services.teacher_modeling import TeacherModel


@dataclass(frozen=True)
class ResponsePackage:
    turn_guidance: str
    teacher_summary: str
    memory_summary: str


def _build_teacher_summary(teacher_model: TeacherModel) -> str:
    expertise = ", ".join(teacher_model.expertise_domains) if teacher_model.expertise_domains else "none yet"
    languages = ", ".join(teacher_model.primary_languages)
    dialects = ", ".join(teacher_model.dialect_tendencies) if teacher_model.dialect_tendencies else "none yet"
    return (
        "## Teacher model\n"
        f"- Credibility score: {teacher_model.credibility_score:.2f}\n"
        f"- Correction density: {teacher_model.correction_density:.2f}\n"
        f"- Preferred register: {teacher_model.preferred_register}\n"
        f"- Teaching style: {teacher_model.teaching_style}\n"
        f"- Expertise domains: {expertise}\n"
        f"- Primary languages: {languages}\n"
        f"- Language mix: {teacher_model.language_mix}\n"
        f"- Dialect hook: {teacher_model.dialect_signature_hook or 'none'}\n"
        f"- Dialect tendencies: {dialects}\n"
        f"- Reliability hook: {teacher_model.reliability_hook}\n"
    )


def build_response_package(
    *,
    teacher_text: str,
    detected_language: str | None,
    teacher_profile: TeacherProfile,
    teacher_model: TeacherModel,
    session_memory: StructuredSessionMemory,
    understanding: InputUnderstanding,
    behavior_policy: BehaviorPolicy,
    question_plan: QuestionPlan,
    response_plan: ResponsePlan,
) -> ResponsePackage:
    teacher_summary = _build_teacher_summary(teacher_model)
    memory_summary = build_memory_summary(session_memory)
    policy_block = behavior_policy.to_prompt_block()
    intelligence_block = (
        "## Input understanding\n"
        f"- Primary language: {understanding.primary_language}\n"
        f"- Secondary languages: {', '.join(understanding.secondary_languages) if understanding.secondary_languages else 'none'}\n"
        f"- Code-switch ratio: {understanding.code_switch_ratio:.2f}\n"
        f"- Teaching intent: {str(understanding.is_teaching).lower()}\n"
        f"- Correction intent: {str(understanding.is_correction).lower()}\n"
        f"- Topic: {understanding.topic}\n"
        f"- Tone: {understanding.tone}\n"
        f"- Emotion: {understanding.emotion}\n"
        f"- Dialect guess: {understanding.dialect_guess or 'none'}\n"
        f"- Dialect confidence: {understanding.dialect_confidence:.2f}\n"
        f"- Speech rate: {understanding.speech_rate}\n"
        f"- Pronunciation style: {understanding.pronunciation_style}\n"
        f"- Prosody pattern: {understanding.prosody_pattern}\n"
        f"- Register estimate: {understanding.register_estimate}\n"
    )
    turn_guidance = build_turn_guidance(
        teacher_text,
        detected_language,
        memory_block=f"{teacher_summary}\n{memory_summary}\n{policy_block}\n{intelligence_block}",
        question_plan=question_plan,
        response_plan=response_plan,
        teacher_profile=teacher_profile,
    )
    return ResponsePackage(
        turn_guidance=turn_guidance,
        teacher_summary=teacher_summary,
        memory_summary=memory_summary,
    )
