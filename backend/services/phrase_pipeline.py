from __future__ import annotations

import httpx
import uuid
import logging
import inspect
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from models.phrases import (
    Phrase,
    PhraseSubmissionGroup,
    PhraseSubmission,
    PhraseSkipEvent,
    PhraseReconfirmationQueue,
    PhraseMetrics
)

from services import stt as stt_svc
from services import hearing as hearing_svc
from services import audio_storage as audio_storage_svc
from services import audio_understanding as audio_understanding_svc
from services import learning as learning_svc

logger = logging.getLogger("lipi.backend.phrase_pipeline")


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def _db_add(db: AsyncSession, item) -> None:
    await _maybe_await(db.add(item))

async def get_next_phrase(db: AsyncSession, user_id: str) -> Phrase | None:
    """Intelligently select the next phrase for the user to teach.
    1. Check reconfirmation queue that is due.
    2. Overweight under-collected phrases.
    3. Exclude phrases they recently answered or skipped.
    """
    
    # Simple check for reconfirmation queue first
    # In a real expanded version, we'd check `scheduled_after_n_prompts` using a prompt counter.
    reconfirm_stmt = select(PhraseReconfirmationQueue).where(
        PhraseReconfirmationQueue.user_id == user_id,
        PhraseReconfirmationQueue.status == "pending"
    ).order_by(PhraseReconfirmationQueue.priority_score.desc()).limit(1)
    
    reconfirm_res = await db.execute(reconfirm_stmt)
    reconfirm_item = await _maybe_await(reconfirm_res.scalar_one_or_none())
    
    if reconfirm_item:
        if isinstance(reconfirm_item, Phrase):
            return reconfirm_item
        phrase = await db.get(Phrase, reconfirm_item.phrase_id)
        if phrase and phrase.is_active:
            return phrase
    
    # Exclude phrases they skipped or completed
    subq_groups = select(PhraseSubmissionGroup.phrase_id).where(PhraseSubmissionGroup.user_id == user_id)
    subq_skips = select(PhraseSkipEvent.phrase_id).where(PhraseSkipEvent.user_id == user_id)
    
    # Find active phrases not done by user
    stmt = select(Phrase).outerjoin(PhraseMetrics, Phrase.id == PhraseMetrics.phrase_id)\
        .where(
            Phrase.is_active == True,
            Phrase.id.not_in(subq_groups),
            Phrase.id.not_in(subq_skips)
        )\
        .order_by(func.coalesce(PhraseMetrics.total_submissions, 0).asc(), func.random())\
        .limit(1)
        
    res = await db.execute(stmt)
    phrase = await _maybe_await(res.scalar_one_or_none())
    return phrase

async def process_phrase_audio(
    db: AsyncSession,
    http: httpx.AsyncClient,
    user_id: str,
    phrase_id: str,
    audio_bytes: bytes,
    audio_uri: str,
    submission_role: str = "primary",  # primary or variation
    variation_type: str | None = None,
    group_id: str | None = None
) -> dict:
    """Processes audio through the core pipeline, saving to DB and learning queue."""
    
    phrase = await db.get(Phrase, phrase_id)
    if not phrase:
        raise ValueError("Phrase not found")

    # STT & Hearing Engine
    stt_result = await stt_svc.transcribe(audio_bytes, http)
    hearing = hearing_svc.analyze_hearing(stt_result)
    
    # Critical Check: Noisy recordings trigger re-record
    if hearing.quality_label == "poor":
        return {
            "status": "retry", 
            "reason": f"Audio quality was too poor (clipping/noise). Let's try again!"
        }
    
    # Audio Semantic/Acoustic extraction (Gemma Audio Sidecar)
    audio_signals = await audio_understanding_svc.extract_audio_signals(
        http=http,
        audio_bytes=audio_bytes,
        rough_transcript=hearing.clean_text
    )
    
    # Note: If it's a rare/Newari language, the STT confidence might be 0.1 but `hearing.quality_label` is ok/good (clean audio).
    # We do NOT reject clean speech.

    # Group Id Persistence
    if not group_id and submission_role == "primary":
        group = PhraseSubmissionGroup(
            phrase_id=phrase_id,
            user_id=user_id,
            status="started"
        )
        await _db_add(db, group)
        await db.flush()
        if not getattr(group, "id", None):
            group.id = str(uuid.uuid4())
        group_id = group.id
        
    if not group_id:
        raise ValueError("Group ID missing for variation track")
        
    submission = PhraseSubmission(
        group_id=group_id,
        phrase_id=phrase_id,
        user_id=user_id,
        audio_uri=audio_uri,
        transcript_text=hearing.clean_text,
        submission_role=submission_role,
        variation_type=variation_type,
        
        # Audio signals mapping
        primary_language=audio_signals.primary_language,
        code_switch_ratio=audio_signals.code_switch_ratio,
        tone=audio_signals.tone,
        emotion=audio_signals.emotion,
        dialect_guess=audio_signals.dialect_guess,
        dialect_confidence=audio_signals.dialect_confidence,
        speech_rate=audio_signals.speech_rate,
        prosody_pattern=audio_signals.prosody_pattern,
        
        stt_confidence=stt_result.get("confidence", 0.0),
        hearing_quality_label=hearing.quality_label
    )
    await _db_add(db, submission)
    
    # Update group status
    group = await db.get(PhraseSubmissionGroup, group_id)
    if group is None or not isinstance(group, PhraseSubmissionGroup):
        group = PhraseSubmissionGroup(id=group_id, phrase_id=phrase_id, user_id=user_id, status="started")
        await _db_add(db, group)
    if submission_role == "primary":
        group.status = "completed"
        
        # Potentially enqueue reconfirmation if STT conf is low but audio clean, or variation ambiguity occurs
        if stt_result.get("confidence", 0.0) < 0.6 and hearing.quality_label != "poor":
            group.requires_reconfirmation = True
            group.reconfirmation_status = "pending"
            await _db_add(db, PhraseReconfirmationQueue(
                phrase_id=phrase_id,
                user_id=user_id,
                original_group_id=group_id,
                priority_score=75.0,
                reason="low_stt_confidence_rare_dialect"
            ))

    # Metrics
    metrics = await db.get(PhraseMetrics, phrase_id)
    if not metrics or not isinstance(metrics, PhraseMetrics):
        metrics = PhraseMetrics(phrase_id=phrase_id)
        await _db_add(db, metrics)
    metrics.voice_submission_count = int(metrics.voice_submission_count or 0) + 1
    metrics.total_submissions = int(metrics.total_submissions or 0) + 1
    
    await db.flush()

    # Enqueue learning cycle async job (same pipeline as Teach)
    await learning_svc.enqueue_phrase_submission(
        submission_id=submission.id,
        user_id=user_id,
        session_id=None,
        phrase_en=phrase.text_en,
        phrase_ne=phrase.text_ne,
        teacher_text=hearing.clean_text,
        stt_result=stt_result,
        audio_path=audio_uri,
        target_language=audio_signals.primary_language
    )
    
    return {
        "status": "success",
        "group_id": group_id,
        "phrase_id": phrase_id,
        "transcript": hearing.clean_text
    }
