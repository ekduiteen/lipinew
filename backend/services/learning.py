"""
Learning cycle — OBSERVE → PROCESS → EXTRACT → STORE

Each teacher turn is queued into Valkey so extraction survives process restarts
and transient failures can be retried without blocking the WebSocket loop.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cache import valkey
from config import settings
from db.connection import SessionLocal

if TYPE_CHECKING:
    pass

logger = logging.getLogger("lipi.backend.learning")

_QUEUE_KEY = settings.learning_queue_key
_PROCESSING_KEY = settings.learning_processing_key
_DEAD_LETTER_KEY = settings.learning_dead_letter_key
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
    audio_path: str | None = None,
    target_language: str | None = None,
) -> None:
    """Persist a learning job to Valkey so extraction is durable and retryable."""
    should_enqueue, reason = _should_learn_from_turn(
        teacher_text=teacher_text,
        lipi_response=lipi_response,
        stt_result=stt_result,
        hearing_result=hearing_result,
        turn_interpretation=turn_interpretation,
        target_language=target_language,
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
    target_language: str | None = None,
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
    newar_targets = {"newar", "newari", "newa", "nepal bhasa"}
    if normalized_target in newar_targets:
        if detected_language not in {"ne", "new"}:
            return False, f"teacher_language={detected_language or 'unknown'}"
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
                audio_path=str(job.get("audio_path") or "") or None,
                target_language=str(job.get("target_language", "") or ""),
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
    audio_path: str | None,
    target_language: str,
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

    if len(teacher_text.strip()) < 3:
        return

    # ── PROCESS — ask LLM to extract vocabulary ──────────────────────────────
    messages = [
        {"role": "system", "content": _EXTRACTION_SYSTEM},
        {
            "role": "user",
            "content": _EXTRACTION_USER.format(
                text=teacher_text,
                response=lipi_response,
            ),
        },
    ]
    raw = await llm_svc.generate(messages, http, stream=False)
    if not isinstance(raw, str):
        return

    # ── EXTRACT — parse JSON ─────────────────────────────────────────────────
    try:
        cleaned = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        payload = json.loads(cleaned)
        words: list[dict] = payload.get("words", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.debug("Extraction JSON parse failed: %s — raw: %r", exc, raw[:200])
        return

    if not words:
        return

    # ── STORE ────────────────────────────────────────────────────────────────
    async with SessionLocal() as db:
        streak = await points_svc.get_current_streak(db, user_id)
        new_word_count = 0

        for entry in words[:5]:
            word = str(entry.get("word", "")).strip().lower()
            language = str(entry.get("language", "ne")).strip()[:10]
            definition_en = str(entry.get("definition_en", "")).strip()[:500]

            if not word or len(word) > 255:
                continue

            new_word_count += await _upsert_vocabulary(
                db=db,
                word=word,
                language=language,
                definition_en=definition_en,
                user_id=user_id,
                session_id=session_id,
                stt_confidence=stt_confidence,
            )

        usage_rule_count = await _store_usage_rules(
            db=db,
            teacher_id=user_id,
            session_id=session_id,
            teacher_text=teacher_text,
            turn_interpretation=turn_interpretation,
            input_understanding=input_understanding,
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

        if turn_interpretation.get("is_correction"):
            logger.info(
                "Captured correction-heavy learning turn topic=%s session=%s",
                turn_interpretation.get("active_topic"),
                session_id,
            )
        if input_understanding.get("is_teaching"):
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


async def _upsert_vocabulary(
    *,
    db: AsyncSession,
    word: str,
    language: str,
    definition_en: str,
    user_id: str,
    session_id: str,
    stt_confidence: float,
) -> int:
    """
    Insert or update a vocabulary entry.
    Returns 1 if truly new (first time LIPI has seen this word), 0 if reinforcement.
    """
    existing = await db.execute(
        text(
            "SELECT id, times_taught, pioneer_teacher_id "
            "FROM vocabulary_entries WHERE word = :w AND language = :l"
        ),
        {"w": word, "l": language},
    )
    row = existing.fetchone()

    is_pioneer = False

    if row is None:
        vocab_id = str(uuid.uuid4())
        previous_confidence = 0.0
        new_confidence = min(stt_confidence, 0.9)
        await db.execute(
            text(
                """
                INSERT INTO vocabulary_entries
                    (id, word, language, definition, confidence, times_taught, pioneer_teacher_id)
                VALUES
                    (:id, :word, :lang, :defn, :conf, 1, :pioneer)
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
        previous_confidence = 0.0
        new_confidence = 0.0
        confidence_row = await db.execute(
            text("SELECT confidence FROM vocabulary_entries WHERE id = :id"),
            {"id": vocab_id},
        )
        confidence_value = confidence_row.scalar()
        previous_confidence = float(confidence_value or 0.0)
        new_confidence = min(previous_confidence + 0.05, 1.0)
        await db.execute(
            text(
                """
                UPDATE vocabulary_entries
                SET times_taught = times_taught + 1,
                    confidence   = LEAST(confidence + 0.05, 1.0),
                    updated_at   = NOW()
                WHERE id = :id
                """
            ),
            {"id": vocab_id},
        )

    await db.execute(
        text(
            """
            INSERT INTO knowledge_confidence_history
                (id, teacher_id, session_id, knowledge_key, language_key, previous_confidence, new_confidence, change_reason, is_contradiction_hook, created_at)
            VALUES
                (:id, :teacher_id, :session_id, :knowledge_key, :language_key, :previous_confidence, :new_confidence, :change_reason, false, NOW())
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
            "change_reason": "learning_turn",
        },
    )

    await db.execute(
        text(
            """
            INSERT INTO vocabulary_teachers
                (id, vocabulary_id, teacher_id, session_id, contribution_type, confidence_added)
            VALUES
                (:id, :vid, :tid, :sid, :ctype, :conf)
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "vid": vocab_id,
            "tid": user_id,
            "sid": session_id,
            "ctype": "first_teach" if is_pioneer else "reinforcement",
            "conf": stt_confidence * 0.1,
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
    audio_path: str | None,
) -> int:
    if not (turn_interpretation.get("is_correction") or input_understanding.get("is_teaching")):
        return 0

    topic_key = str(input_understanding.get("topic") or turn_interpretation.get("active_topic") or "everyday_basics")
    language_key = str(input_understanding.get("primary_language") or "ne")
    rule_type = "correction_rule" if turn_interpretation.get("is_correction") else "teaching_example"
    rule_text = teacher_text.strip()
    if len(rule_text) < 4:
        return 0

    await db.execute(
        text(
            """
            INSERT INTO usage_rules
                (id, teacher_id, session_id, topic_key, language_key, rule_type, rule_text, source_text, confidence, created_at)
            VALUES
                (:id, :teacher_id, :session_id, :topic_key, :language_key, :rule_type, :rule_text, :source_text, :confidence, NOW())
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
            "confidence": max(0.55, min(float(input_understanding.get("transcript_confidence", 0.7)), 0.95)),
        },
    )
    return 1
