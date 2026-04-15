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

from models.message import Message

logger = logging.getLogger("lipi.backend.message_store")


async def persist_teacher_turn(
    db: AsyncSession,
    *,
    session_id: str,
    user_id: str,
    turn_index: int,
    text: str,
    detected_language: str | None = None,
    audio_path: str | None = None,
    stt_confidence: float | None = None,
    audio_duration_ms: int | None = None,
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
        detected_language=detected_language,
        audio_path=audio_path,
        stt_confidence=stt_confidence,
        audio_duration_ms=audio_duration_ms,
        raw_signals_json=raw_signals_json or {},
        derived_signals_json=derived_signals_json or {},
        high_value_signals_json=high_value_signals_json or {},
        style_signals_json=style_signals_json or {},
        prosody_signals_json=prosody_signals_json or {},
        nuance_signals_json=nuance_signals_json or {},
    )
    db.add(msg)
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
