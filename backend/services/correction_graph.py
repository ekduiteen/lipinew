"""Correction graph: persist and query high-value correction events."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.intelligence import (
    CorrectionEvent,
    KnowledgeConfidenceHistory,
    UsageRule,
    ReviewQueueItem,
)
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
        source_audio_path=teacher_message.audio_path,
        is_approved=False
    )
    db.add(event)
    await db.flush()

    # Create UsageRule but mark it as NOT approved yet
    rule = UsageRule(
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
        source_audio_path=teacher_message.audio_path,
        is_approved=False
    )
    db.add(rule)
    await db.flush()

    # Route to HITL Review Queue instead of immediately trusting
    review_item = ReviewQueueItem(
        id=str(uuid.uuid4()),
        source_audio_path=teacher_message.audio_path,
        source_transcript=teacher_message.text,
        teacher_id=teacher_id,
        session_id=session_id,
        extracted_claim=corrected_claim[:500],
        extraction_metadata={
            "correction_event_id": event.id,
            "usage_rule_id": rule.id,
            "topic": topic,
            "wrong_claim": wrong_message.text if wrong_message else "",
            "language_key": language_key,
        },
        confidence=float(confidence_after or 0.8),
        model_source="hybrid_input_understanding",
        status="pending_review"
    )
    db.add(review_item)
    await db.flush()
    
    # We DO NOT generate a KnowledgeConfidenceHistory bump here anymore
    # That happens asynchronously if the Admin Review Queue approves the item.

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


async def load_approved_rules_for_teacher(
    db: AsyncSession,
    *,
    teacher_id: str,
    language_key: str | None = None,
    limit: int = 5,
) -> list[UsageRule]:
    """Read admin-approved usage rules so they can be re-injected into future sessions."""
    stmt = (
        select(UsageRule)
        .where(
            UsageRule.teacher_id == teacher_id,
            UsageRule.is_approved.is_(True),
        )
        .order_by(desc(UsageRule.created_at))
        .limit(limit)
    )
    if language_key:
        stmt = stmt.where(UsageRule.language_key == language_key)
    rows = await db.execute(stmt)
    return list(rows.scalars())
