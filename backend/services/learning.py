"""
Learning cycle — OBSERVE → PROCESS → EXTRACT → STORE

Each teacher turn is queued into Valkey so extraction survives process restarts
and transient failures can be retried without blocking the WebSocket loop.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cache import valkey
from config import settings
from db.connection import SessionLocal
from models.intelligence import ReviewQueueItem
from services import hearing as hearing_svc
from services import keyterm_service as keyterm_service_svc
from services import transcript_repair as transcript_repair_svc
from services import turn_intelligence as turn_intelligence_svc
from services.language_registry import load_language_profile

if TYPE_CHECKING:
    pass

logger = logging.getLogger("lipi.backend.learning")

_QUEUE_KEY = settings.learning_queue_key
_PROCESSING_KEY = settings.learning_processing_key
_DEAD_LETTER_KEY = settings.learning_dead_letter_key
_MAX_QUEUE_DEPTH = 2000  # drop new jobs if backlog exceeds this
_CONFUSED_REPLY_MARKERS = (
    "मलाई थाहा भएन",
    "के तिमीले फेरि भन्न सक्छौ",
    "कृपया फेरि भन्नुहोस्",
    "मैले गलत बुझें",
    "के मैले सही बुझें",
    "मलाई लाग्छ",
)
_HINDI_REPLY_MARKERS = (
    "कैसे",
    "क्या",
    "है",
    "हूँ",
    "हैं",
    "नहीं",
    "लेकिन",
)
_LEARNER_META_REPLY_MARKERS = (
    "तपाईंले मलाई सिकाउनुभयो",
    "तपाईंले भन्नुभयो",
    "म सिक्नको लागि",
    "मलाई यो नयाँ कुरा सिक्न",
    "मलाई धेरै रमाइलो लाग्यो",
    "मलाई धेरै मन लाग्यो",
    "म विद्यार्थी हुँ",
    "you are teaching me",
    "i am excited to learn",
    "i understand,",
    "oh, i understand",
)
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]")
_STOPWORDS = {"हो", "छ", "र", "त", "the", "and", "a", "an", "to"}


# ─── Extraction prompt ───────────────────────────────────────────────────────

_EXTRACTION_SYSTEM = """\
You are a linguistic data extractor. Extract vocabulary words from the teacher's utterance.
Return ONLY valid JSON — no prose, no markdown.

Format:
{"words": [{"word": "...", "language": "ne|en|...", "definition_en": "..."}]}

Rules:
- Only include content words (nouns, verbs, adjectives, adverbs). Skip pronouns, particles, conjunctions.
- Max 5 words per turn.
- If no new vocabulary, return {"words": []}.
- language code must be a valid BCP-47 subtag (e.g. ne, en, mai, new).
"""

_EXTRACTION_USER = """\
Teacher's utterance: "{text}"
LIPI's response (context): "{response}"
"""


# ─── Queue lifecycle ─────────────────────────────────────────────────────────

async def enqueue_turn(
    *,
    session_id: str,
    user_id: str,
    teacher_text: str,
    lipi_response: str,
    stt_result: dict,
    hearing_result: dict | None = None,
    turn_interpretation: dict | None = None,
    input_understanding: dict | None = None,
    behavior_policy: dict | None = None,
    teacher_message_id: str | None = None,
    turn_intelligence: dict | None = None,
    audio_path: str | None = None,
    target_language: str | None = None,
    session_language_contract: dict | None = None,
    normalized_transcript: str | None = None,
    training_tier: str | None = None,
    asr_drift_type: str | None = None,
) -> None:
    """Persist a learning job to Valkey so extraction is durable and retryable."""
    should_enqueue, reason = _should_learn_from_turn(
        teacher_text=teacher_text,
        lipi_response=lipi_response,
        stt_result=stt_result,
        hearing_result=hearing_result,
        turn_interpretation=turn_interpretation,
        input_understanding=input_understanding,
        target_language=target_language,
        session_language_contract=session_language_contract,
        training_tier=training_tier,
        asr_drift_type=asr_drift_type,
    )
    if not should_enqueue:
        logger.info("Skipping learning enqueue: %s", reason)
        return

    job = {
        "job_id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": user_id,
        "teacher_text": teacher_text,
        "lipi_response": lipi_response,
        "stt_result": stt_result,
        "hearing_result": hearing_result or {},
        "turn_interpretation": turn_interpretation or {},
        "input_understanding": input_understanding or {},
        "behavior_policy": behavior_policy or {},
        "teacher_message_id": teacher_message_id,
        "turn_intelligence": turn_intelligence or {},
        "audio_path": audio_path,
        "target_language": target_language or "",
        "session_language_contract": session_language_contract or {},
        "normalized_transcript": normalized_transcript or "",
        "training_tier": training_tier or "",
        "asr_drift_type": asr_drift_type or "",
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
        "job_type": "turn"
    }
    queue_depth = await valkey.llen(_QUEUE_KEY)
    if queue_depth >= _MAX_QUEUE_DEPTH:
        logger.warning(
            "Learning queue at capacity (%d) — dropping job session=%s",
            queue_depth,
            session_id,
        )
        return
    await valkey.lpush(_QUEUE_KEY, json.dumps(job))


async def enqueue_phrase_submission(
    *,
    submission_id: str,
    user_id: str,
    session_id: str | None,
    phrase_en: str,
    phrase_ne: str,
    teacher_text: str,
    stt_result: dict,
    audio_path: str | None = None,
    target_language: str | None = None,
) -> None:
    """Persist a phrase lab submission to Valkey for vocabulary extraction."""
    # We bypass the conversational filters and enqueue directly
    if len(teacher_text.strip()) < 2:
        logger.info("Skipping phrase learning enqueue: text too short")
        return

    job = {
        "job_id": str(uuid.uuid4()),
        "job_type": "phrase",
        "submission_id": submission_id,
        "session_id": session_id or "",
        "user_id": user_id,
        "teacher_text": teacher_text,
        "lipi_response": f"[Phrase Prompt]: {phrase_en} -> {phrase_ne}",
        "stt_result": stt_result,
        "hearing_result": {},
        "turn_interpretation": {"active_topic": "phrase_lab"},
        "input_understanding": {"primary_language": "ne", "topic": "phrase_lab"},
        "behavior_policy": {},
        "audio_path": audio_path,
        "target_language": target_language or "",
        "attempt": 0,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }
    await valkey.lpush(_QUEUE_KEY, json.dumps(job))


def _should_learn_from_turn(
    *,
    teacher_text: str,
    lipi_response: str,
    stt_result: dict,
    hearing_result: dict | None = None,
    turn_interpretation: dict | None = None,
    input_understanding: dict | None = None,
    target_language: str | None = None,
    session_language_contract: dict | None = None,
    training_tier: str | None = None,
    asr_drift_type: str | None = None,
) -> tuple[bool, str]:
    teacher_text = teacher_text.strip()
    lipi_response = lipi_response.strip()
    detected_language = str(stt_result.get("language", "") or "").strip().lower()
    stt_confidence = float(stt_result.get("confidence", 0.0) or 0.0)
    if hearing_result:
        if not bool(hearing_result.get("learning_allowed", True)):
            return False, f"hearing_blocked={','.join(hearing_result.get('reason_codes', [])) or 'unknown'}"

    if len(teacher_text) < 3:
        return False, "teacher_text_too_short"

    normalized_target = (target_language or "").strip().lower()
    contract = session_language_contract or {}
    base_asr_languages = {
        str(item).lower()
        for item in contract.get("base_asr_languages", [])
    }
    if training_tier == "rejected":
        return False, "training_tier_rejected"
    if asr_drift_type == "wrong_target_language":
        return False, "wrong_target_language"
    if normalized_target:
        try:
            language_profile = load_language_profile(normalized_target)
            inheritance = {
                normalized_target,
                *[str(item).lower() for item in language_profile.get("inherits_from", [])],
            }
        except ValueError:
            inheritance = {normalized_target}
        acceptable_languages = inheritance | base_asr_languages
        if detected_language and detected_language not in acceptable_languages and detected_language != "unknown":
            return False, f"teacher_language={detected_language}"
    elif detected_language != settings.learning_required_teacher_language:
        return False, f"teacher_language={detected_language or 'unknown'}"

    if stt_confidence < settings.learning_min_stt_confidence:
        return False, f"low_stt_confidence={stt_confidence:.2f}"

    if not lipi_response:
        return False, "empty_lipi_response"

    if len(lipi_response) > settings.learning_max_reply_chars:
        return False, f"reply_too_long={len(lipi_response)}"

    lowered_reply = lipi_response.lower()
    if any(marker in lipi_response for marker in _CONFUSED_REPLY_MARKERS):
        return False, "assistant_confused"

    if any(marker in lowered_reply for marker in _HINDI_REPLY_MARKERS):
        return False, "assistant_hindi_mixed"

    if any(marker in lowered_reply for marker in _LEARNER_META_REPLY_MARKERS):
        return False, "assistant_learner_meta"

    if turn_interpretation:
        intent_type = str(turn_interpretation.get("intent_type") or "")
        if intent_type == "unknown" and len(teacher_text.split()) < 5:
            return False, "low_signal_unknown_intent"
    if input_understanding:
        if str(input_understanding.get("intent_label") or "") == "low_signal":
            return False, "low_signal_turn_intelligence"
        if input_understanding.get("usable_for_learning") is False:
            return False, f"turn_quality={input_understanding.get('unusable_reason') or 'blocked'}"

    return True, "ok"


async def requeue_inflight_jobs() -> int:
    """Move unacked jobs back to the pending queue on startup."""
    moved = 0
    while True:
        raw = await valkey.rpoplpush(_PROCESSING_KEY, _QUEUE_KEY)
        if raw is None:
            break
        moved += 1
    if moved:
        logger.warning("Requeued %d in-flight learning job(s) after restart", moved)
    return moved


async def run_worker(http: httpx.AsyncClient) -> None:
    """Consume queued learning jobs forever."""
    await requeue_inflight_jobs()
    logger.info("Learning worker online")

    while True:
        raw = await valkey.brpoplpush(
            _QUEUE_KEY,
            _PROCESSING_KEY,
            timeout=settings.learning_worker_poll_seconds,
        )
        if raw is None:
            continue

        try:
            job = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Dropping malformed learning job: %r", raw[:200])
            await valkey.lrem(_PROCESSING_KEY, 1, raw)
            continue

        try:
            await _run(
                session_id=str(job["session_id"]),
                user_id=str(job["user_id"]),
                teacher_text=str(job["teacher_text"]),
                lipi_response=str(job["lipi_response"]),
                stt_result=dict(job.get("stt_result", {})),
                hearing_result=dict(job.get("hearing_result", {})),
                turn_interpretation=dict(job.get("turn_interpretation", {})),
                input_understanding=dict(job.get("input_understanding", {})),
                behavior_policy=dict(job.get("behavior_policy", {})),
                teacher_message_id=str(job.get("teacher_message_id") or "") or None,
                turn_intelligence=dict(job.get("turn_intelligence") or {}),
                audio_path=str(job.get("audio_path") or "") or None,
                target_language=str(job.get("target_language", "") or ""),
                session_language_contract=dict(job.get("session_language_contract") or {}),
                normalized_transcript=str(job.get("normalized_transcript") or ""),
                training_tier=str(job.get("training_tier") or ""),
                asr_drift_type=str(job.get("asr_drift_type") or ""),
                http=http,
            )
            await valkey.lrem(_PROCESSING_KEY, 1, raw)
        except Exception as exc:
            attempt = int(job.get("attempt", 0)) + 1
            job["attempt"] = attempt
            job["last_error"] = str(exc)
            job["failed_at"] = datetime.now(timezone.utc).isoformat()
            await valkey.lrem(_PROCESSING_KEY, 1, raw)

            if attempt >= settings.learning_max_attempts:
                await valkey.lpush(_DEAD_LETTER_KEY, json.dumps(job))
                logger.warning(
                    "Learning job moved to dead letter queue after %d attempt(s): session=%s job=%s error=%s",
                    attempt,
                    job.get("session_id"),
                    job.get("job_id"),
                    exc,
                )
            else:
                await valkey.lpush(_QUEUE_KEY, json.dumps(job))
                logger.warning(
                    "Learning job retry %d/%d queued: session=%s job=%s error=%s",
                    attempt,
                    settings.learning_max_attempts,
                    job.get("session_id"),
                    job.get("job_id"),
                    exc,
                )


# ─── Main worker step ────────────────────────────────────────────────────────

async def _run(
    *,
    session_id: str,
    user_id: str,
    teacher_text: str,
    lipi_response: str,
    stt_result: dict,
    hearing_result: dict,
    turn_interpretation: dict,
    input_understanding: dict,
    behavior_policy: dict,
    teacher_message_id: str | None,
    turn_intelligence: dict,
    audio_path: str | None,
    target_language: str,
    session_language_contract: dict,
    normalized_transcript: str,
    training_tier: str,
    asr_drift_type: str,
    http: httpx.AsyncClient,
) -> None:
    from services import llm as llm_svc
    from services import points as points_svc
    from services import speaker_embeddings as speaker_embeddings_svc

    # ── OBSERVE ───────────────────────────────────────────────────────────────
    stt_confidence: float = stt_result.get("confidence", 0.0)
    audio_quality_ok: bool = stt_confidence >= settings.learning_min_stt_confidence

    if hearing_result and not bool(hearing_result.get("learning_allowed", True)):
        logger.debug("Hearing gate blocked learning: %s", hearing_result.get("reason_codes"))
        return

    if not audio_quality_ok:
        logger.debug("Low STT confidence (%.2f) — skipping extraction", stt_confidence)
        return
    if training_tier == "rejected":
        logger.debug("Rejected training tier — skipping extraction")
        return

    if len(teacher_text.strip()) < 3:
        return

    if turn_intelligence:
        live_analysis = turn_intelligence_svc.from_dict(turn_intelligence)
    else:
        hearing = hearing_svc.analyze_hearing(stt_result)
        repair = transcript_repair_svc.TranscriptRepairResult(
            original_text=teacher_text,
            repaired_text=teacher_text,
            confidence_after=stt_confidence,
        )
        live_analysis = turn_intelligence_svc.analyze_turn(
            hearing=hearing,
            repaired_transcript=repair,
            keyterms=keyterm_service_svc.KeytermPreparation(),
            memory_context={},
        )

    authoritative_analysis = live_analysis
    try:
        authoritative_analysis = await turn_intelligence_svc.enrich_with_llm(
            teacher_text=teacher_text,
            live_analysis=live_analysis,
            http=http,
        )
    except Exception as exc:
        logger.debug("Turn intelligence enrichment failed: %s", exc)

    # ── STORE ────────────────────────────────────────────────────────────────
    async with SessionLocal() as db:
        if teacher_message_id:
            await turn_intelligence_svc.persist_turn_intelligence(
                db,
                message_id=teacher_message_id,
                session_id=session_id,
                teacher_id=user_id,
                transcript_original=authoritative_analysis.transcript_repair.original_text or teacher_text,
                transcript_final=authoritative_analysis.transcript_repair.repaired_text or teacher_text,
                intelligence=authoritative_analysis,
            )

        if (
            not authoritative_analysis.quality.usable_for_learning
            or (
                authoritative_analysis.intent.confidence < settings.learning_min_intent_confidence
                and authoritative_analysis.intent.label != "correction"
            )
        ):
            await db.commit()
            logger.info(
                "Learning gated by turn intelligence intent=%s quality=%s reason=%s session=%s",
                authoritative_analysis.intent.label,
                authoritative_analysis.quality.usable_for_learning,
                authoritative_analysis.quality.reason_if_not,
                session_id,
            )
            return

        streak = await points_svc.get_current_streak(db, user_id)
        new_word_count = 0
        low_trust_count = 0
        eligible_entities = [
            entity
            for entity in authoritative_analysis.entities
            if entity.entity_type
            in {
                "vocabulary",
                "proper_name",
                "phrase",
                "honorific_or_register_term",
                "language_name",
                "pronunciation_target",
                "cultural_concept",
                "corrected_term",
            }
            and entity.confidence >= settings.learning_min_entity_confidence
        ]

        gloss_lookup = {
            entity.normalized_text: entity.text
            for entity in authoritative_analysis.entities
            if entity.entity_type == "gloss_or_meaning"
        }

        for entity in eligible_entities[:5]:
            word = str(entity.normalized_text or "").strip().lower()
            language = str(entity.language or authoritative_analysis.code_switch.primary_language or "ne").strip()[:10]
            definition_en = str(gloss_lookup.get(word, ""))[:500]
            if not word or len(word) > 255:
                continue

            is_valid, validation_reason = _validate_extraction(
                word=word,
                language=language,
                teacher_text=teacher_text,
            )
            if not is_valid:
                low_trust_count += await _flag_low_trust_extraction(
                    db=db,
                    teacher_id=user_id,
                    session_id=session_id,
                    teacher_text=teacher_text,
                    word=word,
                    language=language,
                    reason=validation_reason,
                    stt_confidence=stt_confidence,
                    audio_path=audio_path,
                )
                logger.info(
                    "Rejected extraction word=%r language=%s reason=%s session=%s",
                    word,
                    language,
                    validation_reason,
                    session_id,
                )
                continue

            new_word_count += await _upsert_vocabulary(
                db=db,
                word=word,
                language=language,
                definition_en=definition_en,
                user_id=user_id,
                session_id=session_id,
                stt_confidence=stt_confidence,
                entity_confidence=entity.confidence,
                learning_weight=authoritative_analysis.learning_weight,
                intent_label=authoritative_analysis.intent.label,
                keyterm_hit=word in {str(value).strip().lower() for value in authoritative_analysis.keyterms.get("applied", [])},
            )

        usage_rule_count = await _store_usage_rules(
            db=db,
            teacher_id=user_id,
            session_id=session_id,
            teacher_text=teacher_text,
            turn_interpretation=turn_interpretation,
            input_understanding=input_understanding,
            turn_intelligence=authoritative_analysis.to_dict(),
            audio_path=audio_path,
        )
        speaker_embedding_stored = False
        speaker_embedding_reason = "not_attempted"
        if audio_path:
            speaker_embedding_stored, speaker_embedding_reason = await speaker_embeddings_svc.extract_and_store(
                db=db,
                http=http,
                teacher_id=user_id,
                session_id=session_id,
                audio_path=audio_path,
                detected_language=str(input_understanding.get("primary_language") or stt_result.get("language") or ""),
                stt_confidence=stt_confidence,
                hearing_result=hearing_result,
            )

        for _ in range(new_word_count):
            await points_svc.log_transaction(
                db,
                user_id=user_id,
                session_id=session_id,
                event_type="word_learned",
                current_streak=streak,
            )

        if new_word_count > 0:
            await db.commit()
            logger.info(
                "Learned %d new word(s) — session=%s user=%s",
                new_word_count,
                session_id,
                user_id,
            )
        elif usage_rule_count > 0:
            await db.commit()
        elif speaker_embedding_stored:
            await db.commit()
        elif low_trust_count > 0:
            await db.commit()

        if authoritative_analysis.intent.label == "correction" or turn_interpretation.get("is_correction"):
            logger.info(
                "Captured correction-heavy learning turn topic=%s session=%s",
                turn_interpretation.get("active_topic"),
                session_id,
            )
        if authoritative_analysis.intent.label in {"teaching", "example", "register_instruction", "pronunciation_guidance", "code_switch_explanation"} or input_understanding.get("is_teaching"):
            logger.info(
                "Teaching turn preserved for async learning topic=%s language=%s policy=%s",
                input_understanding.get("topic"),
                input_understanding.get("primary_language"),
                behavior_policy.get("confirmation_style"),
            )
        if speaker_embedding_stored:
            logger.info("Speaker embedding captured session=%s user=%s", session_id, user_id)
        elif audio_path:
            logger.debug(
                "Speaker embedding skipped session=%s user=%s reason=%s",
                session_id,
                user_id,
                speaker_embedding_reason,
            )

        logger.debug(
            "Learning metadata session=%s target=%s training_tier=%s drift=%s normalized=%s contract=%s",
            session_id,
            target_language,
            training_tier,
            asr_drift_type,
            bool(normalized_transcript),
            bool(session_language_contract),
        )


def _validate_extraction(*, word: str, language: str, teacher_text: str) -> tuple[bool, str]:
    normalized_word = word.strip().lower()
    normalized_text = teacher_text.strip().lower()
    if not normalized_word:
        return False, "empty_word"
    if len(normalized_word) <= 1:
        return False, "too_short"
    if normalized_word in _STOPWORDS:
        return False, "stopword"
    if language == "ne" and not _DEVANAGARI_RE.search(normalized_word):
        if normalized_word not in normalized_text:
            return False, "script_mismatch"
    if language == "en" and not _LATIN_WORD_RE.search(normalized_word):
        return False, "script_mismatch"
    if normalized_word not in normalized_text:
        return False, "not_in_transcript"
    return True, "ok"


async def _flag_low_trust_extraction(
    *,
    db: AsyncSession,
    teacher_id: str,
    session_id: str,
    teacher_text: str,
    word: str,
    language: str,
    reason: str,
    stt_confidence: float,
    audio_path: str | None,
) -> int:
    db.add(
        ReviewQueueItem(
            id=str(uuid.uuid4()),
            source_audio_path=audio_path,
            source_transcript=teacher_text[:1500],
            teacher_id=teacher_id,
            session_id=session_id or None,
            extracted_claim=word,
            extraction_metadata={
                "review_kind": "low_trust_extraction",
                "reason": reason,
                "language_key": language,
            },
            confidence=min(max(stt_confidence, 0.05), 0.49),
            model_source="learning_validation_guard",
            status="pending_review",
        )
    )
    return 1


async def _upsert_vocabulary(
    *,
    db: AsyncSession,
    word: str,
    language: str,
    definition_en: str,
    user_id: str,
    session_id: str,
    stt_confidence: float,
    entity_confidence: float,
    learning_weight: float,
    intent_label: str,
    keyterm_hit: bool,
) -> int:
    """
    Insert or update a vocabulary entry.
    Returns 1 if truly new (first time LIPI has seen this word), 0 if reinforcement.
    """
    existing = await db.execute(
        text(
            "SELECT id, times_taught, pioneer_teacher_id, confidence "
            "FROM vocabulary_entries WHERE word = :w AND language = :l"
        ),
        {"w": word, "l": language},
    )
    row = existing.fetchone()

    is_pioneer = False

    if row is None:
        vocab_id = str(uuid.uuid4())
        previous_confidence = 0.0
        initial_confidence = max(
            min(stt_confidence, 0.6),
            min(entity_confidence * 0.75, 0.62),
        )
        if intent_label == "correction":
            initial_confidence = min(initial_confidence + 0.08, 0.7)
        if keyterm_hit:
            initial_confidence = min(initial_confidence + 0.03, 0.72)
        new_confidence = round(initial_confidence, 3)
        await db.execute(
            text(
                """
                INSERT INTO vocabulary_entries
                    (id, word, language, definition, confidence, times_taught, pioneer_teacher_id, distinct_teacher_count, admin_approved, created_at, updated_at)
                VALUES
                    (:id, :word, :lang, :defn, :conf, 1, :pioneer, 1, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": vocab_id,
                "word": word,
                "lang": language,
                "defn": definition_en,
                "conf": new_confidence,
                "pioneer": user_id,
            },
        )
        is_pioneer = True
    else:
        vocab_id = str(row[0])
        previous_confidence = float(row[3] or 0.0)  # confidence included in initial SELECT
        new_confidence = 0.0
        teacher_count_row = await db.execute(
            text("SELECT COUNT(DISTINCT teacher_id) FROM vocabulary_teachers WHERE vocabulary_id = :id"),
            {"id": vocab_id},
        )
        distinct_teachers = int(teacher_count_row.scalar() or 0)
        teacher_seen_row = await db.execute(
            text("SELECT 1 FROM vocabulary_teachers WHERE vocabulary_id = :id AND teacher_id = :teacher_id LIMIT 1"),
            {"id": vocab_id, "teacher_id": user_id},
        )
        teacher_already_seen = teacher_seen_row.scalar() is not None
        if not teacher_already_seen:
            distinct_teachers += 1
        cap = 0.95 if distinct_teachers >= 2 else 0.70
        increment = 0.03 + min(entity_confidence * 0.04, 0.04) + min(learning_weight * 0.03, 0.03)
        if intent_label == "correction":
            increment += 0.03
        if keyterm_hit:
            increment += 0.02
        new_confidence = min(previous_confidence + increment, cap)
        await db.execute(
            text(
                """
                UPDATE vocabulary_entries
                SET times_taught = times_taught + 1,
                    confidence   = CASE
                        WHEN confidence + :increment < :cap THEN confidence + :increment
                        ELSE :cap
                    END,
                    distinct_teacher_count = :distinct_teacher_count,
                    updated_at   = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {
                "id": vocab_id,
                "cap": cap,
                "increment": increment,
                "distinct_teacher_count": distinct_teachers,
            },
        )

    await db.execute(
        text(
            """
            INSERT INTO knowledge_confidence_history
                (id, teacher_id, session_id, knowledge_key, language_key, previous_confidence, new_confidence, change_reason, is_contradiction_hook, created_at)
            VALUES
                (:id, :teacher_id, :session_id, :knowledge_key, :language_key, :previous_confidence, :new_confidence, :change_reason, false, CURRENT_TIMESTAMP)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "teacher_id": user_id,
            "session_id": session_id,
            "knowledge_key": word,
            "language_key": language,
            "previous_confidence": previous_confidence,
            "new_confidence": new_confidence,
            "change_reason": f"learning_turn:{intent_label}",
        },
    )

    await db.execute(
        text(
            """
            INSERT INTO vocabulary_teachers
                (id, vocabulary_id, teacher_id, session_id, contribution_type, confidence_added, created_at)
            VALUES
                (:id, :vid, :tid, :sid, :ctype, :conf, CURRENT_TIMESTAMP)
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "vid": vocab_id,
            "tid": user_id,
            "sid": session_id,
            "ctype": "first_teach" if is_pioneer else "reinforcement",
            "conf": min((stt_confidence * 0.05) + (entity_confidence * 0.05), 0.1),
        },
    )

    if is_pioneer:
        from services import points as points_svc

        streak = await points_svc.get_current_streak(db, user_id)
        await points_svc.log_transaction(
            db,
            user_id=user_id,
            session_id=session_id,
            event_type="pioneer_word",
            current_streak=streak,
            meta={"word": word, "language": language},
        )

    return 1 if is_pioneer else 0


async def _store_usage_rules(
    *,
    db: AsyncSession,
    teacher_id: str,
    session_id: str,
    teacher_text: str,
    turn_interpretation: dict,
    input_understanding: dict,
    turn_intelligence: dict,
    audio_path: str | None,
) -> int:
    intent = str((turn_intelligence.get("intent") or {}).get("label") or "")
    if not (
        turn_interpretation.get("is_correction")
        or input_understanding.get("is_teaching")
        or intent in {"register_instruction", "pronunciation_guidance", "code_switch_explanation"}
    ):
        return 0

    topic_key = str(input_understanding.get("topic") or turn_interpretation.get("active_topic") or "everyday_basics")
    language_key = str(input_understanding.get("primary_language") or "ne")
    if intent == "register_instruction":
        rule_type = "register_instruction"
    elif intent == "pronunciation_guidance":
        rule_type = "pronunciation_note"
    elif intent == "code_switch_explanation":
        rule_type = "code_switch_note"
    elif turn_interpretation.get("is_correction"):
        rule_type = "correction_rule"
    else:
        rule_type = "teaching_example"
    rule_text = teacher_text.strip()
    if len(rule_text) < 4:
        return 0

    await db.execute(
        text(
            """
            INSERT INTO usage_rules
                (id, teacher_id, session_id, topic_key, language_key, rule_type, rule_text, source_text, confidence, created_at)
            VALUES
                (:id, :teacher_id, :session_id, :topic_key, :language_key, :rule_type, :rule_text, :source_text, :confidence, CURRENT_TIMESTAMP)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "teacher_id": teacher_id,
            "session_id": session_id,
            "topic_key": topic_key,
            "language_key": language_key,
            "rule_type": rule_type,
            "rule_text": rule_text[:1500],
            "source_text": audio_path or teacher_text[:500],
            "confidence": max(
                0.55,
                min(
                    float((turn_intelligence.get("quality") or {}).get("usability_score") or input_understanding.get("transcript_confidence", 0.7)),
                    0.95,
                ),
            ),
        },
    )
    return 1
