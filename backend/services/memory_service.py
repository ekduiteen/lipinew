"""Structured session memory with hot Valkey state and durable DB snapshots."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from cache import valkey
from models.intelligence import SessionMemorySnapshot


_MEMORY_KEY = "session:{session_id}:structured_memory"
_MEMORY_TTL_SECONDS = 60 * 60 * 6


@dataclass(frozen=True)
class StructuredSessionMemory:
    active_language: str | None
    active_topic: str | None
    recent_taught_words: list[str]
    recent_corrections: list[str]
    unresolved_misunderstandings: list[str]
    next_followup_goal: str | None
    user_style: str
    style_memory: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _empty_memory() -> StructuredSessionMemory:
    return StructuredSessionMemory(
        active_language=None,
        active_topic=None,
        recent_taught_words=[],
        recent_corrections=[],
        unresolved_misunderstandings=[],
        next_followup_goal=None,
        user_style="neutral",
        style_memory={},
    )


async def load_session_memory(
    db: AsyncSession,
    *,
    session_id: str,
    teacher_id: str,
) -> StructuredSessionMemory:
    raw = await valkey.get(_MEMORY_KEY.format(session_id=session_id))
    if raw:
        try:
            return StructuredSessionMemory(**json.loads(raw))
        except Exception:
            pass

    row = await db.execute(
        select(SessionMemorySnapshot)
        .where(
            SessionMemorySnapshot.session_id == session_id,
            SessionMemorySnapshot.teacher_id == teacher_id,
        )
        .order_by(desc(SessionMemorySnapshot.created_at))
        .limit(1)
    )
    snapshot = row.scalar_one_or_none()
    if snapshot is None:
        return _empty_memory()

    memory = StructuredSessionMemory(
        active_language=snapshot.active_language,
        active_topic=snapshot.active_topic,
        recent_taught_words=list(snapshot.recent_taught_words or []),
        recent_corrections=list(snapshot.recent_corrections or []),
        unresolved_misunderstandings=list(snapshot.unresolved_misunderstandings or []),
        next_followup_goal=snapshot.next_followup_goal,
        user_style=snapshot.user_style,
        style_memory=dict(snapshot.style_memory_json or {}),
    )
    await valkey.setex(_MEMORY_KEY.format(session_id=session_id), _MEMORY_TTL_SECONDS, json.dumps(memory.to_dict()))
    return memory


async def load_teacher_long_term_memory(
    db: AsyncSession,
    *,
    teacher_id: str,
) -> StructuredSessionMemory:
    row = await db.execute(
        select(SessionMemorySnapshot)
        .where(SessionMemorySnapshot.teacher_id == teacher_id)
        .order_by(desc(SessionMemorySnapshot.created_at))
        .limit(1)
    )
    snapshot = row.scalar_one_or_none()
    if snapshot is None:
        return _empty_memory()
    return StructuredSessionMemory(
        active_language=snapshot.active_language,
        active_topic=snapshot.active_topic,
        recent_taught_words=list(snapshot.recent_taught_words or []),
        recent_corrections=list(snapshot.recent_corrections or []),
        unresolved_misunderstandings=list(snapshot.unresolved_misunderstandings or []),
        next_followup_goal=snapshot.next_followup_goal,
        user_style=snapshot.user_style,
        style_memory=dict(snapshot.style_memory_json or {}),
    )


async def update_session_memory(
    db: AsyncSession,
    *,
    session_id: str,
    teacher_id: str,
    turn_index: int,
    existing: StructuredSessionMemory,
    active_language: str | None,
    active_topic: str | None,
    taught_terms: list[str],
    correction_text: str | None,
    misunderstanding_text: str | None,
    next_followup_goal: str | None,
    user_style: str,
    style_memory: dict | None = None,
) -> StructuredSessionMemory:
    recent_taught = list(dict.fromkeys((existing.recent_taught_words + taught_terms)))[-8:]
    recent_corrections = existing.recent_corrections.copy()
    if correction_text:
        recent_corrections = (recent_corrections + [correction_text])[-5:]

    misunderstandings = existing.unresolved_misunderstandings.copy()
    if misunderstanding_text:
        misunderstandings = (misunderstandings + [misunderstanding_text])[-4:]
    elif misunderstandings:
        misunderstandings = misunderstandings[-2:]

    updated = StructuredSessionMemory(
        active_language=active_language or existing.active_language,
        active_topic=active_topic or existing.active_topic,
        recent_taught_words=recent_taught,
        recent_corrections=recent_corrections,
        unresolved_misunderstandings=misunderstandings,
        next_followup_goal=next_followup_goal or existing.next_followup_goal,
        user_style=user_style or existing.user_style,
        style_memory={**existing.style_memory, **(style_memory or {})},
    )

    snapshot = SessionMemorySnapshot(
        id=str(uuid.uuid4()),
        session_id=session_id,
        teacher_id=teacher_id,
        turn_index=turn_index,
        active_language=updated.active_language,
        active_topic=updated.active_topic,
        recent_taught_words=updated.recent_taught_words,
        recent_corrections=updated.recent_corrections,
        unresolved_misunderstandings=updated.unresolved_misunderstandings,
        next_followup_goal=updated.next_followup_goal,
        user_style=updated.user_style,
        style_memory_json=updated.style_memory,
    )
    db.add(snapshot)
    await db.flush()
    await valkey.setex(_MEMORY_KEY.format(session_id=session_id), _MEMORY_TTL_SECONDS, json.dumps(updated.to_dict()))
    return updated


def build_memory_summary(memory: StructuredSessionMemory) -> str:
    return (
        "## Structured memory\n"
        f"- Active language: {memory.active_language or 'unknown'}\n"
        f"- Active topic: {memory.active_topic or 'unknown'}\n"
        f"- Recent taught words: {', '.join(memory.recent_taught_words) if memory.recent_taught_words else 'none'}\n"
        f"- Recent corrections: {', '.join(memory.recent_corrections) if memory.recent_corrections else 'none'}\n"
        f"- Unresolved misunderstandings: {', '.join(memory.unresolved_misunderstandings) if memory.unresolved_misunderstandings else 'none'}\n"
        f"- Next follow-up goal: {memory.next_followup_goal or 'none'}\n"
        f"- User style: {memory.user_style}\n"
        f"- Style memory: {memory.style_memory or 'none'}\n"
    )
