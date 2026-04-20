"""Teacher modeling: build and update a structured teacher profile for response behavior."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.curriculum import UserCurriculumProfile
from models.intelligence import CorrectionEvent, TeacherCredibilityEvent, TeacherSignal
from models.message import Message
from models.user import User
from services.input_understanding import InputUnderstanding


@dataclass(frozen=True)
class TeacherModel:
    teacher_id: str
    credibility_score: float
    correction_density: float
    preferred_register: str
    teaching_style: str
    expertise_domains: list[str]
    primary_languages: list[str]
    language_mix: dict
    dialect_signature_hook: str | None
    dialect_tendencies: list[str]
    consistency_score: float
    reliability_hook: str

    def to_dict(self) -> dict:
        return asdict(self)


def _derive_teaching_style(
    *,
    correction_density: float,
    active_register: str,
    code_switch_tendency: float,
) -> str:
    if correction_density >= 0.3:
        return "correction_heavy"
    if active_register in {"tapai", "hajur"}:
        return "formal_guided"
    if code_switch_tendency >= 0.35:
        return "multilingual_bridge"
    return "steady_teacher"


def _derive_reliability_hook(credibility_score: float, consistency_score: float) -> str:
    if credibility_score >= 0.75 and consistency_score >= 0.7:
        return "high_trust"
    if credibility_score <= 0.35:
        return "low_trust"
    return "normal_trust"


async def _load_recent_signal_tendencies(db: AsyncSession, teacher_id: str) -> tuple[list[str], dict]:
    rows = (
        await db.execute(
            select(TeacherSignal).where(TeacherSignal.teacher_id == teacher_id).order_by(TeacherSignal.created_at.desc()).limit(40)
        )
    ).scalars().all()

    dialect_scores: dict[str, int] = {}
    language_mix: dict[str, int] = {}
    for row in rows:
        if row.signal_key == "dialect_guess":
            guess = str((row.signal_value_json or {}).get("value") or "").strip()
            if guess:
                dialect_scores[guess] = dialect_scores.get(guess, 0) + 1
        if row.signal_key == "primary_language":
            language = str((row.signal_value_json or {}).get("value") or "").strip()
            if language:
                language_mix[language] = language_mix.get(language, 0) + 1
        if row.signal_key == "secondary_languages":
            for language in (row.signal_value_json or {}).get("value", []) or []:
                lang_value = str(language).strip()
                if lang_value:
                    language_mix[lang_value] = language_mix.get(lang_value, 0) + 1

    ranked_dialects = [dialect for dialect, _ in sorted(dialect_scores.items(), key=lambda item: item[1], reverse=True)[:3]]
    return ranked_dialects, language_mix


async def build_teacher_model(
    db: AsyncSession,
    *,
    user: User,
    profile: UserCurriculumProfile,
) -> TeacherModel:
    correction_count = (
        await db.execute(
            select(func.count()).select_from(CorrectionEvent).where(CorrectionEvent.teacher_id == user.id)
        )
    ).scalar_one()
    teacher_turn_count = (
        await db.execute(
            select(func.count()).select_from(Message).where(
                Message.teacher_id == user.id,
                Message.role == "teacher",
            )
        )
    ).scalar_one()
    credibility_event_count = (
        await db.execute(
            select(func.count()).select_from(TeacherCredibilityEvent).where(
                TeacherCredibilityEvent.teacher_id == user.id
            )
        )
    ).scalar_one()

    correction_density = round(correction_count / max(teacher_turn_count, 1), 3)
    consistency_score = round(
        min(1.0, 0.45 + (credibility_event_count * 0.04) + (profile.conversation_turn_count * 0.01)),
        3,
    )
    dialect_signature_hook = None
    primary_language = (user.primary_language or "nepali").lower()
    if primary_language in {"newar", "newari", "nepal bhasa", "newa"}:
        dialect_signature_hook = "newari_teacher"
    elif user.hometown:
        dialect_signature_hook = f"region:{user.hometown.lower()[:24]}"

    expertise_domains = []
    if profile.last_topic:
        expertise_domains.append(profile.last_topic)
    if profile.assigned_lane == "regional_lane":
        expertise_domains.append("regional_variation")
    if correction_density >= 0.2:
        expertise_domains.append("corrections")
    expertise_domains = list(dict.fromkeys(expertise_domains))

    credibility_score = float(user.credibility_score or 0.5)
    teaching_style = _derive_teaching_style(
        correction_density=correction_density,
        active_register=profile.active_register,
        code_switch_tendency=profile.code_switch_tendency,
    )
    reliability_hook = _derive_reliability_hook(credibility_score, consistency_score)
    primary_languages = [str(user.primary_language or "Nepali")]
    for language in user.other_languages or []:
        lang_value = str(language)
        if lang_value not in primary_languages:
            primary_languages.append(lang_value)

    dialect_tendencies, observed_language_mix = await _load_recent_signal_tendencies(db, user.id)
    if not observed_language_mix:
        observed_language_mix = {lang.lower(): 1 for lang in primary_languages}

    return TeacherModel(
        teacher_id=user.id,
        credibility_score=credibility_score,
        correction_density=correction_density,
        preferred_register=profile.active_register,
        teaching_style=teaching_style,
        expertise_domains=expertise_domains,
        primary_languages=primary_languages,
        language_mix=observed_language_mix,
        dialect_signature_hook=dialect_signature_hook,
        dialect_tendencies=dialect_tendencies,
        consistency_score=consistency_score,
        reliability_hook=reliability_hook,
    )


async def record_teacher_signals(
    db: AsyncSession,
    *,
    teacher_id: str,
    session_id: str,
    message_id: str | None,
    understanding: InputUnderstanding,
    source: str = "input_understanding_v1",
) -> None:
    signal_specs = [
        ("intent", "intent_label", understanding.intent_label, understanding.intent_confidence),
        ("language", "primary_language", understanding.primary_language, 0.85),
        ("language", "secondary_languages", understanding.secondary_languages, 0.65),
        ("language", "code_switch_ratio", {"value": understanding.code_switch_ratio}, 0.65),
        ("style", "register_estimate", understanding.register_estimate, 0.7),
        ("style", "tone", understanding.tone, 0.7),
        ("style", "speech_rate", understanding.speech_rate, 0.55),
        ("style", "pronunciation_style", understanding.pronunciation_style, 0.55),
        ("style", "prosody_pattern", understanding.prosody_pattern, 0.5),
        ("quality", "usable_for_learning", understanding.usable_for_learning, 0.8),
    ]
    if understanding.dialect_guess:
        signal_specs.append(
            ("dialect", "dialect_guess", understanding.dialect_guess, understanding.dialect_confidence)
        )

    for signal_type, signal_key, value, confidence in signal_specs:
        stored_value = value if isinstance(value, dict) else {"value": value}
        signal = TeacherSignal(
            id=str(uuid.uuid4()),
            teacher_id=teacher_id,
            session_id=session_id,
            message_id=message_id,
            signal_type=signal_type,
            signal_key=signal_key,
            signal_value_json=stored_value,
            confidence=max(0.0, min(float(confidence), 1.0)),
            source=source,
        )
        db.add(signal)
    await db.flush()


async def log_credibility_event(
    db: AsyncSession,
    *,
    teacher_id: str,
    event_type: str,
    score_delta: float,
    resulting_score: float,
    session_id: str | None = None,
    detail: str | None = None,
) -> TeacherCredibilityEvent:
    event = TeacherCredibilityEvent(
        id=str(uuid.uuid4()),
        teacher_id=teacher_id,
        session_id=session_id,
        event_type=event_type,
        score_delta=score_delta,
        resulting_score=resulting_score,
        detail=detail,
    )
    db.add(event)
    await db.flush()
    return event


async def apply_teacher_turn_outcome(
    db: AsyncSession,
    *,
    user: User,
    understanding_is_correction: bool,
    understanding_is_teaching: bool,
    transcript_confidence: float,
    session_id: str,
) -> float:
    score_delta = 0.0
    event_type = "steady_turn"
    detail = None

    if understanding_is_correction:
        score_delta += 0.03
        event_type = "correction_signal"
        detail = "Teacher corrected LIPI"
    elif understanding_is_teaching and transcript_confidence >= 0.82:
        score_delta += 0.015
        event_type = "high_conf_teaching"
        detail = "Clear teaching turn"
    elif transcript_confidence < 0.6:
        score_delta -= 0.01
        event_type = "low_conf_turn"
        detail = "Low confidence turn"

    new_score = max(0.05, min(float(user.credibility_score or 0.5) + score_delta, 0.99))
    user.credibility_score = new_score
    user.updated_at = datetime.now(timezone.utc)
    await log_credibility_event(
        db,
        teacher_id=user.id,
        session_id=session_id,
        event_type=event_type,
        score_delta=score_delta,
        resulting_score=new_score,
        detail=detail,
    )
    return new_score
