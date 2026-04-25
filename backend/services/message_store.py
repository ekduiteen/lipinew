"""
Message persistence — writes every conversation turn to the messages table.
Previously turns were only in Valkey (1h TTL). This makes them permanent.
"""

from __future__ import annotations

import uuid
import time
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from models.asr_candidate import ASRCandidate
from models.asr_error_event import ASRErrorEvent
from models.message import Message
from models.text_corpus_item import TextCorpusItem

logger = logging.getLogger("lipi.backend.message_store")


async def persist_teacher_turn(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: str,
    turn_index: int,
    text: str,
    detected_language: str | None = None,
    country_code: str | None = None,
    target_language: str | None = None,
    bridge_language: str | None = None,
    script: str | None = None,
    dialect_label: str | None = None,
    selected_language: str | None = None,
    code_switch_ratio: float | None = None,
    asr_drift_type: str | None = None,
    needs_teacher_confirmation: bool = False,
    audio_quality: float | None = None,
    audio_path: str | None = None,
    stt_confidence: float | None = None,
    teacher_verified: bool = False,
    audio_duration_ms: int | None = None,
    raw_stt: str | None = None,
    base_candidate_transcript: str | None = None,
    english_candidate_transcript: str | None = None,
    target_candidate_transcript: str | None = None,
    acoustic_transcript: str | None = None,
    normalized_transcript: str | None = None,
    teacher_corrected_transcript: str | None = None,
    correction_error_type: str | None = None,
    correction_error_family: str | None = None,
    training_tier: str | None = None,
    training_eligible: bool = False,
    consent_training_use: bool = False,
    candidates: list[dict] | None = None,
    raw_signals_json: dict | None = None,
    derived_signals_json: dict | None = None,
    high_value_signals_json: dict | None = None,
    style_signals_json: dict | None = None,
    prosody_signals_json: dict | None = None,
    nuance_signals_json: dict | None = None,
) -> Message:
    msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        teacher_id=user_id,
        turn_index=turn_index,
        role="teacher",
        text=text,
        country_code=country_code,
        target_language=target_language,
        bridge_language=bridge_language,
        script=script,
        dialect_label=dialect_label,
        detected_language=detected_language,
        selected_language=selected_language,
        code_switch_ratio=code_switch_ratio,
        asr_drift_type=asr_drift_type,
        needs_teacher_confirmation=needs_teacher_confirmation,
        audio_quality=audio_quality,
        audio_path=audio_path,
        stt_confidence=stt_confidence,
        teacher_verified=teacher_verified,
        audio_duration_ms=audio_duration_ms,
        raw_stt=raw_stt,
        base_candidate_transcript=base_candidate_transcript,
        english_candidate_transcript=english_candidate_transcript,
        target_candidate_transcript=target_candidate_transcript,
        acoustic_transcript=acoustic_transcript,
        normalized_transcript=normalized_transcript,
        teacher_corrected_transcript=teacher_corrected_transcript,
        correction_error_type=correction_error_type,
        correction_error_family=correction_error_family,
        training_tier=training_tier,
        training_eligible=training_eligible,
        consent_training_use=consent_training_use,
        raw_signals_json=raw_signals_json or {},
        derived_signals_json=derived_signals_json or {},
        high_value_signals_json=high_value_signals_json or {},
        style_signals_json=style_signals_json or {},
        prosody_signals_json=prosody_signals_json or {},
        nuance_signals_json=nuance_signals_json or {},
    )
    db.add(msg)
    await db.flush()
    for index, candidate in enumerate(candidates or [], start=1):
        db.add(
            ASRCandidate(
                message_id=msg.id,
                candidate_type=str(candidate.get("candidate_type") or "candidate"),
                language_code=str(candidate.get("language_code") or "") or None,
                transcript=str(candidate.get("transcript") or "") or None,
                normalized_transcript=str(candidate.get("normalized_transcript") or "") or None,
                confidence=float(candidate.get("confidence") or 0.0),
                model_name=str(candidate.get("model_name") or "") or None,
                adapter_name=str(candidate.get("adapter_name") or "") or None,
                rank=int(candidate.get("rank") or index),
                selected=bool(candidate.get("selected", False)),
                metadata_json=dict(candidate.get("metadata") or {}),
            )
        )
    await db.flush()
    return msg


async def persist_lipi_turn(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: str,
    turn_index: int,
    text: str,
    llm_model: str | None = None,
    llm_latency_ms: int | None = None,
    derived_signals_json: dict | None = None,
    style_signals_json: dict | None = None,
) -> Message:
    msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        teacher_id=user_id,
        turn_index=turn_index,
        role="lipi",
        text=text,
        llm_model=llm_model,
        llm_latency_ms=llm_latency_ms,
        derived_signals_json=derived_signals_json or {},
        style_signals_json=style_signals_json or {},
    )
    db.add(msg)
    await db.flush()
    return msg


async def get_turn_count(db: AsyncSession, session_id: str) -> int:
    """Returns current number of turns in this session (for turn_index)."""
    result = await db.execute(
        select(func.count()).where(Message.session_id == session_id)
    )
    return result.scalar() or 0


async def apply_teacher_correction(
    db: AsyncSession,
    *,
    message: Message,
    teacher_id: str,
    corrected_text: str | None,
    normalized_transcript: str | None,
    asr_drift_type: str,
    correction_error_type: str | None,
    correction_error_family: str | None,
    training_tier: str,
    training_eligible: bool,
    consent_training_use: bool,
    source_type: str,
    meaning_nepali: str | None = None,
    meaning_english: str | None = None,
    correction_metadata: dict | None = None,
) -> Message:
    message.teacher_corrected_transcript = corrected_text
    message.normalized_transcript = normalized_transcript
    message.teacher_verified = source_type != "skip"
    message.asr_drift_type = asr_drift_type
    message.correction_error_type = correction_error_type
    message.correction_error_family = correction_error_family
    message.training_tier = training_tier
    message.training_eligible = training_eligible
    message.consent_training_use = consent_training_use
    if source_type == "wrong_language":
        message.needs_teacher_confirmation = True

    db.add(
        ASRErrorEvent(
            message_id=message.id,
            teacher_id=teacher_id,
            country_code=message.country_code,
            target_language=message.target_language,
            base_asr_languages=(correction_metadata or {}).get("base_asr_languages", []),
            script=message.script,
            raw_stt=message.raw_stt,
            teacher_correction=corrected_text,
            error_type=correction_error_type,
            error_family=correction_error_family,
            severity="high" if source_type == "wrong_language" else "medium",
            audio_quality=message.audio_quality,
            stt_confidence=message.stt_confidence,
            teacher_verified=True,
            training_tier=training_tier,
            metadata_json=correction_metadata or {"source_type": source_type},
        )
    )

    if corrected_text:
        db.add(
            TextCorpusItem(
                teacher_id=teacher_id,
                country_code=message.country_code,
                language_code=message.target_language,
                script=message.script,
                dialect_label=message.dialect_label,
                source_type=source_type,
                raw_text=corrected_text,
                normalized_text=normalized_transcript,
                meaning_nepali=meaning_nepali,
                meaning_english=meaning_english,
                verified=True,
                consent_training_use=consent_training_use,
                metadata_json=correction_metadata or {},
            )
        )

    await db.flush()
    return message
