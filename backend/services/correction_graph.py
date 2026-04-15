"""Correction graph: persist and query high-value correction events."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.intelligence import CorrectionEvent, KnowledgeConfidenceHistory, UsageRule
from models.message import Message


@dataclass(frozen=True)
class CorrectionSummary:
    recent_count: int
    last_correction: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def infer_correction_type(text: str) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in ("not like that", "होइन", "instead")):
        return "replacement"
    if any(marker in lowered for marker in ("when", "used", "प्रयोग", "used")):
        return "usage"
    return "direct_correction"


async def get_previous_lipi_message(
    db: AsyncSession,
    *,
    session_id: str,
    before_turn_index: int,
) -> Message | None:
    row = await db.execute(
        select(Message)
        .where(
            Message.session_id == session_id,
            Message.role == "lipi",
            Message.turn_index < before_turn_index,
        )
        .order_by(desc(Message.turn_index))
        .limit(1)
    )
    return row.scalar_one_or_none()


async def record_correction_event(
    db: AsyncSession,
    *,
    session_id: str,
    teacher_id: str,
    teacher_message: Message,
    wrong_message: Message | None,
    corrected_claim: str,
    correction_type: str,
    topic: str | None,
    language_key: str,
    confidence_before: float | None,
    confidence_after: float | None,
) -> CorrectionEvent:
    event = CorrectionEvent(
        id=str(uuid.uuid4()),
        session_id=session_id,
        teacher_id=teacher_id,
        wrong_message_id=wrong_message.id if wrong_message else None,
        correction_message_id=teacher_message.id,
        wrong_claim=wrong_message.text if wrong_message else "",
        corrected_claim=corrected_claim,
        correction_type=correction_type,
        confidence_before=confidence_before,
        confidence_after=confidence_after,
        topic=topic,
        language_key=language_key,
    )
    db.add(event)
    await db.flush()

    db.add(
        KnowledgeConfidenceHistory(
            id=str(uuid.uuid4()),
            teacher_id=teacher_id,
            session_id=session_id,
            correction_event_id=event.id,
            knowledge_key=topic or "correction",
            language_key=language_key,
            previous_confidence=float(confidence_before or 0.3),
            new_confidence=float(confidence_after or 0.8),
            change_reason="teacher_correction",
            is_contradiction_hook=True,
        )
    )
    db.add(
        UsageRule(
            id=str(uuid.uuid4()),
            teacher_id=teacher_id,
            session_id=session_id,
            correction_event_id=event.id,
            topic_key=topic,
            language_key=language_key,
            rule_type="correction_rule",
            rule_text=corrected_claim[:500],
            source_text=wrong_message.text[:500] if wrong_message else None,
            confidence=float(confidence_after or 0.8),
        )
    )
    await db.flush()
    return event


async def get_recent_correction_summary(
    db: AsyncSession,
    *,
    teacher_id: str,
    limit: int = 5,
) -> CorrectionSummary:
    rows = await db.execute(
        select(CorrectionEvent)
        .where(CorrectionEvent.teacher_id == teacher_id)
        .order_by(desc(CorrectionEvent.created_at))
        .limit(limit)
    )
    events = list(rows.scalars())
    return CorrectionSummary(
        recent_count=len(events),
        last_correction=events[0].corrected_claim if events else None,
    )
