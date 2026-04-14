"""
Learning cycle — OBSERVE → PROCESS → EXTRACT → STORE

Runs as a background asyncio task after each teacher turn so it never
adds latency to the WebSocket conversation loop.

OBSERVE:  capture STT confidence, audio quality signal
PROCESS:  ask the LLM to identify new vocabulary words from the utterance
EXTRACT:  parse the structured response
STORE:    upsert vocabulary_entries + vocabulary_teachers, log word_learned points

Uses the same vLLM connection as the conversation — lightweight extraction
prompt (~100 tokens in, ~200 tokens out), routed through llm.generate().
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import SessionLocal

if TYPE_CHECKING:
    pass

logger = logging.getLogger("lipi.backend.learning")

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


# ─── Main entry point ────────────────────────────────────────────────────────

async def process_turn_background(
    *,
    session_id: str,
    user_id: str,
    teacher_text: str,
    lipi_response: str,
    stt_result: dict,
    http: httpx.AsyncClient,
) -> None:
    """
    Fire-and-forget background task.
    Call with: asyncio.create_task(process_turn_background(...))
    """
    try:
        await _run(
            session_id=session_id,
            user_id=user_id,
            teacher_text=teacher_text,
            lipi_response=lipi_response,
            stt_result=stt_result,
            http=http,
        )
    except Exception as exc:
        logger.warning("Learning cycle error (session=%s): %s", session_id, exc)


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
    audio_quality_ok: bool = stt_confidence >= 0.6

    if not audio_quality_ok:
        logger.debug("Low STT confidence (%.2f) — skipping extraction", stt_confidence)
        return

    if len(teacher_text.strip()) < 3:
        return

    # ── PROCESS — ask LLM to extract vocabulary ───────────────────────────────
    messages = [
        {"role": "system", "content": _EXTRACTION_SYSTEM},
        {
            "role": "user",
            "content": _EXTRACTION_USER.format(
                text=teacher_text, response=lipi_response
            ),
        },
    ]
    raw = await llm_svc.generate(messages, http, stream=False)
    if not isinstance(raw, str):
        return

    # ── EXTRACT — parse JSON ──────────────────────────────────────────────────
    try:
        # Strip any accidental markdown fencing
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        payload = json.loads(cleaned)
        words: list[dict] = payload.get("words", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.debug("Extraction JSON parse failed: %s — raw: %r", exc, raw[:200])
        return

    if not words:
        return

    # ── STORE ─────────────────────────────────────────────────────────────────
    async with SessionLocal() as db:
        streak = await points_svc.get_current_streak(db, user_id)
        new_word_count = 0

        for entry in words[:5]:  # hard cap
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

        # Log points for new words
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
                new_word_count, session_id, user_id,
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
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    # Check if word already exists
    result = await db.execute(
        select(
            # We import the raw table here to avoid circular ORM issues
            # vocabulary_entries is defined in init-db.sql, not as an ORM model yet
        ).where(False)  # placeholder — replaced below
    )

    # Use raw SQL via text() to avoid needing a full ORM model for vocabulary_entries
    from sqlalchemy import text

    existing = await db.execute(
        text("SELECT id, times_taught, pioneer_teacher_id FROM vocabulary_entries WHERE word = :w AND language = :l"),
        {"w": word, "l": language},
    )
    row = existing.fetchone()

    is_pioneer = False

    if row is None:
        # Brand new word — insert, mark pioneer
        vocab_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO vocabulary_entries
                    (id, word, language, definition, confidence, times_taught, pioneer_teacher_id)
                VALUES
                    (:id, :word, :lang, :defn, :conf, 1, :pioneer)
            """),
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
        # Reinforce existing word — bump count and nudge confidence up
        await db.execute(
            text("""
                UPDATE vocabulary_entries
                SET times_taught = times_taught + 1,
                    confidence   = LEAST(confidence + 0.05, 1.0),
                    updated_at   = NOW()
                WHERE id = :id
            """),
            {"id": vocab_id},
        )

    # Record teacher contribution
    await db.execute(
        text("""
            INSERT INTO vocabulary_teachers
                (id, vocabulary_id, teacher_id, session_id, contribution_type, confidence_added)
            VALUES
                (:id, :vid, :tid, :sid, :ctype, :conf)
            ON CONFLICT DO NOTHING
        """),
        {
            "id": str(uuid.uuid4()),
            "vid": vocab_id,
            "tid": user_id,
            "sid": session_id,
            "ctype": "first_teach" if is_pioneer else "reinforcement",
            "conf": stt_confidence * 0.1,
        },
    )

    # Pioneer bonus points (separate from word_learned — handled by caller)
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
