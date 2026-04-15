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
) -> None:
    """Persist a learning job to Valkey so extraction is durable and retryable."""
    should_enqueue, reason = _should_learn_from_turn(
        teacher_text=teacher_text,
        lipi_response=lipi_response,
        stt_result=stt_result,
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
        "attempt": 0,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }
    await valkey.lpush(_QUEUE_KEY, json.dumps(job))


def _should_learn_from_turn(
    *,
    teacher_text: str,
    lipi_response: str,
    stt_result: dict,
) -> tuple[bool, str]:
    teacher_text = teacher_text.strip()
    lipi_response = lipi_response.strip()
    detected_language = str(stt_result.get("language", "") or "").strip().lower()
    stt_confidence = float(stt_result.get("confidence", 0.0) or 0.0)

    if len(teacher_text) < 3:
        return False, "teacher_text_too_short"

    if detected_language != settings.learning_required_teacher_language:
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
    http: httpx.AsyncClient,
) -> None:
    from services import llm as llm_svc
    from services import points as points_svc

    # ── OBSERVE ───────────────────────────────────────────────────────────────
    stt_confidence: float = stt_result.get("confidence", 0.0)
    audio_quality_ok: bool = stt_confidence >= settings.learning_min_stt_confidence

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
                "conf": min(stt_confidence, 0.9),
                "pioneer": user_id,
            },
        )
        is_pioneer = True
    else:
        vocab_id = str(row[0])
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
