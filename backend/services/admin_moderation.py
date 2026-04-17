from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.admin_control import AdminAccount, AdminAuditLog
from models.dataset_gold import GoldRecord
from models.intelligence import (
    CorrectionEvent,
    KnowledgeConfidenceHistory,
    ReviewQueueItem,
    UsageRule,
)
from models.message import Message

logger = logging.getLogger("lipi.backend.admin.moderation")

CLAIM_TIMEOUT = timedelta(minutes=10)


@dataclass(frozen=True)
class ModerationFilters:
    review_type: str | None = None
    language: str | None = None
    confidence_min: float | None = None
    confidence_max: float | None = None
    source: str | None = None
    age_order: str = "oldest"
    claimed: str = "all"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def claim_expiry_cutoff(now: datetime | None = None) -> datetime:
    return (now or _now_utc()) - CLAIM_TIMEOUT


def _json_text_expr(db: AsyncSession, key: str):
    column = ReviewQueueItem.extraction_metadata
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        return func.json_extract(column, f"$.{key}")
    return column.op("->>")(key)


def _apply_queue_filters(
    stmt,
    *,
    db: AsyncSession,
    filters: ModerationFilters,
    admin_id: str | None = None,
):
    review_kind_expr = _json_text_expr(db, "review_kind")
    correction_event_expr = _json_text_expr(db, "correction_event_id")
    language_expr = _json_text_expr(db, "language_key")

    if filters.review_type == "correction":
        stmt = stmt.where(correction_event_expr.is_not(None))
    elif filters.review_type == "low_trust_extraction":
        stmt = stmt.where(review_kind_expr == "low_trust_extraction")

    if filters.language:
        stmt = stmt.where(language_expr == filters.language)
    if filters.confidence_min is not None:
        stmt = stmt.where(ReviewQueueItem.confidence >= filters.confidence_min)
    if filters.confidence_max is not None:
        stmt = stmt.where(ReviewQueueItem.confidence <= filters.confidence_max)

    if filters.source == "human":
        stmt = stmt.where(correction_event_expr.is_not(None))
    elif filters.source == "model":
        stmt = stmt.where(
            or_(
                review_kind_expr == "low_trust_extraction",
                correction_event_expr.is_(None),
            )
        )

    cutoff = claim_expiry_cutoff()
    if filters.claimed == "mine" and admin_id:
        stmt = stmt.where(
            ReviewQueueItem.claimed_by == admin_id,
            ReviewQueueItem.claimed_at.is_not(None),
            ReviewQueueItem.claimed_at >= cutoff,
        )
    elif filters.claimed == "unclaimed":
        stmt = stmt.where(ReviewQueueItem.claimed_by.is_(None))

    order_column = ReviewQueueItem.created_at.asc() if filters.age_order != "newest" else ReviewQueueItem.created_at.desc()
    return stmt.order_by(order_column)


async def release_expired_claims(db: AsyncSession, *, now: datetime | None = None) -> int:
    cutoff = claim_expiry_cutoff(now)
    result = await db.execute(
        update(ReviewQueueItem)
        .where(
            ReviewQueueItem.status == "pending_review",
            ReviewQueueItem.claimed_at.is_not(None),
            ReviewQueueItem.claimed_at < cutoff,
        )
        .values(claimed_by=None, claimed_at=None)
        .execution_options(synchronize_session=False)
    )
    return int(result.rowcount or 0)


def _with_row_lock(stmt, db: AsyncSession):
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        return stmt
    return stmt.with_for_update(skip_locked=True)


async def claim_next_review_item(
    db: AsyncSession,
    *,
    admin: AdminAccount,
    filters: ModerationFilters,
) -> ReviewQueueItem | None:
    await release_expired_claims(db)

    stmt = select(ReviewQueueItem).where(
        ReviewQueueItem.status == "pending_review",
        ReviewQueueItem.claimed_by.is_(None),
    )
    stmt = _apply_queue_filters(stmt, db=db, filters=filters, admin_id=admin.id).limit(1)
    stmt = _with_row_lock(stmt, db)

    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        await db.commit()
        return None

    item.claimed_by = admin.id
    item.claimed_at = _now_utc()
    await db.commit()
    await db.refresh(item)
    return item


async def claim_review_buffer(
    db: AsyncSession,
    *,
    admin: AdminAccount,
    filters: ModerationFilters,
    limit: int = 3,
) -> list[ReviewQueueItem]:
    claimed: list[ReviewQueueItem] = []
    for _ in range(max(limit, 0)):
        item = await claim_next_review_item(db, admin=admin, filters=filters)
        if item is None:
            break
        claimed.append(item)
    return claimed


async def list_review_queue(
    db: AsyncSession,
    *,
    admin: AdminAccount,
    filters: ModerationFilters,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[ReviewQueueItem], int]:
    await release_expired_claims(db)

    base_stmt = select(ReviewQueueItem).where(ReviewQueueItem.status == "pending_review")
    filtered_stmt = _apply_queue_filters(base_stmt, db=db, filters=filters, admin_id=admin.id)
    total_stmt = select(func.count()).select_from(filtered_stmt.subquery())

    rows = await db.execute(filtered_stmt.offset(offset).limit(limit))
    total = await db.scalar(total_stmt) or 0
    await db.commit()
    return list(rows.scalars()), int(total)


def _claim_is_active(item: ReviewQueueItem) -> bool:
    return bool(item.claimed_by and item.claimed_at and item.claimed_at >= claim_expiry_cutoff())


def _ensure_actionable(item: ReviewQueueItem, admin: AdminAccount) -> None:
    if item.status != "pending_review":
        raise ValueError(f"Review item {item.id} is not pending")
    if _claim_is_active(item) and item.claimed_by != admin.id:
        raise PermissionError(f"Review item {item.id} is claimed by another moderator")


async def _label_and_promote_to_gold_no_commit(
    db: AsyncSession,
    *,
    item: ReviewQueueItem,
    admin: AdminAccount,
    corrected_transcript: str,
    dialect: str | None = None,
    register: str | None = None,
    tags: list[str] | None = None,
    audio_quality: float = 1.0,
    noise_level: str = "low",
    notes: str | None = None,
) -> GoldRecord:
    _ensure_actionable(item, admin)

    item.status = "approved"
    item.claimed_by = None
    item.claimed_at = None

    metadata = item.extraction_metadata or {}
    correction_event_id = metadata.get("correction_event_id")
    usage_rule_id = metadata.get("usage_rule_id")
    language_key = metadata.get("language_key") or "ne"

    correction_event: CorrectionEvent | None = None
    if correction_event_id:
        correction_event = await db.get(CorrectionEvent, correction_event_id)
        if correction_event is not None:
            correction_event.is_approved = True
            correction_event.confidence_after = max(float(correction_event.confidence_after or 0.0), 0.95)

    if usage_rule_id:
        usage_rule = await db.get(UsageRule, usage_rule_id)
        if usage_rule is not None:
            usage_rule.is_approved = True
            usage_rule.confidence = max(float(usage_rule.confidence or 0.0), 0.9)

    db.add(
        KnowledgeConfidenceHistory(
            id=str(uuid.uuid4()),
            teacher_id=item.teacher_id,
            session_id=item.session_id,
            correction_event_id=correction_event_id,
            knowledge_key=(corrected_transcript or item.extracted_claim or "")[:255],
            language_key=language_key,
            previous_confidence=0.5,
            new_confidence=0.95,
            change_reason="admin_approved_correction",
            is_contradiction_hook=False,
        )
    )

    gold = GoldRecord(
        id=str(uuid.uuid4()),
        original_message_id=metadata.get("message_id"),
        session_id=item.session_id,
        teacher_id=item.teacher_id,
        audio_path=item.source_audio_path,
        raw_transcript=item.source_transcript or "",
        corrected_transcript=corrected_transcript,
        dialect=dialect,
        register=register,
        primary_language=language_key,
        tags=tags or [],
        audio_quality_score=audio_quality,
        noise_level=noise_level,
        labeled_by=admin.id,
    )
    db.add(gold)

    if correction_event is not None and correction_event.correction_message_id:
        await db.execute(
            update(Message)
            .where(Message.id == correction_event.correction_message_id)
            .values(text=corrected_transcript)
        )

    if corrected_transcript:
        await db.execute(
            update(ReviewQueueItem)
            .where(ReviewQueueItem.id == item.id)
            .values(extracted_claim=corrected_transcript)
        )

    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="approve_and_label",
            entity_type="GoldRecord",
            entity_id=gold.id,
            details={
                "review_item_id": item.id,
                "dialect": dialect,
                "register": register,
                "tags": tags or [],
                "notes": notes,
            },
        )
    )
    return gold


async def label_and_promote_to_gold(
    db: AsyncSession,
    item_id: str,
    admin: AdminAccount,
    corrected_transcript: str,
    dialect: str | None = None,
    register: str | None = None,
    tags: list[str] | None = None,
    audio_quality: float = 1.0,
    noise_level: str = "low",
    notes: str | None = None,
) -> GoldRecord:
    item = await db.get(ReviewQueueItem, item_id)
    if not item:
        raise ValueError("Review item not found")

    gold = await _label_and_promote_to_gold_no_commit(
        db,
        item=item,
        admin=admin,
        corrected_transcript=corrected_transcript,
        dialect=dialect,
        register=register,
        tags=tags,
        audio_quality=audio_quality,
        noise_level=noise_level,
        notes=notes,
    )
    await db.commit()
    await db.refresh(gold)
    return gold


async def batch_label_and_promote_to_gold(
    db: AsyncSession,
    *,
    item_specs: Sequence[dict],
    admin: AdminAccount,
) -> list[GoldRecord]:
    item_ids = [str(spec["id"]) for spec in item_specs]
    if not item_ids:
        return []

    await release_expired_claims(db)
    stmt = select(ReviewQueueItem).where(ReviewQueueItem.id.in_(item_ids))
    if db.bind is None or db.bind.dialect.name != "sqlite":
        stmt = stmt.with_for_update()
    rows = await db.execute(stmt)
    items = {item.id: item for item in rows.scalars()}
    if len(items) != len(set(item_ids)):
        raise ValueError("One or more review items were not found")

    created: list[GoldRecord] = []
    for spec in item_specs:
        item = items[str(spec["id"])]
        corrected_transcript = str(spec.get("corrected_transcript") or item.extracted_claim or "").strip()
        if not corrected_transcript:
            raise ValueError(f"Review item {item.id} has no transcript to approve")
        created.append(
            await _label_and_promote_to_gold_no_commit(
                db,
                item=item,
                admin=admin,
                corrected_transcript=corrected_transcript,
                dialect=spec.get("dialect"),
                register=spec.get("register_label") or spec.get("register"),
                tags=list(spec.get("tags") or []),
                audio_quality=float(spec.get("audio_quality", 1.0)),
                noise_level=str(spec.get("noise_level", "low")),
                notes=spec.get("notes"),
            )
        )

    await db.commit()
    for gold in created:
        await db.refresh(gold)
    return created


async def reject_review_item(
    db: AsyncSession,
    item_id: str,
    admin: AdminAccount,
    reason: str,
) -> None:
    item = await db.get(ReviewQueueItem, item_id)
    if not item:
        raise ValueError("Review item not found")
    _ensure_actionable(item, admin)

    item.status = "rejected"
    item.claimed_by = None
    item.claimed_at = None
    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="reject_turn",
            entity_type="ReviewQueueItem",
            entity_id=item_id,
            details={"reason": reason},
        )
    )
    await db.commit()


async def batch_reject_review_items(
    db: AsyncSession,
    *,
    item_ids: Sequence[str],
    admin: AdminAccount,
    reason: str,
) -> int:
    if not item_ids:
        return 0

    await release_expired_claims(db)
    stmt = select(ReviewQueueItem).where(ReviewQueueItem.id.in_(list(item_ids)))
    if db.bind is None or db.bind.dialect.name != "sqlite":
        stmt = stmt.with_for_update()
    rows = await db.execute(stmt)
    items = list(rows.scalars())
    if len(items) != len(set(item_ids)):
        raise ValueError("One or more review items were not found")

    for item in items:
        _ensure_actionable(item, admin)
        item.status = "rejected"
        item.claimed_by = None
        item.claimed_at = None
        db.add(
            AdminAuditLog(
                admin_id=admin.id,
                action="reject_turn",
                entity_type="ReviewQueueItem",
                entity_id=item.id,
                details={"reason": reason, "batch": True},
            )
        )

    await db.commit()
    return len(items)


async def release_review_items(
    db: AsyncSession,
    *,
    item_ids: Sequence[str],
    admin: AdminAccount,
) -> int:
    if not item_ids:
        return 0

    result = await db.execute(
        update(ReviewQueueItem)
        .where(
            ReviewQueueItem.id.in_(list(item_ids)),
            ReviewQueueItem.status == "pending_review",
            ReviewQueueItem.claimed_by == admin.id,
        )
        .values(claimed_by=None, claimed_at=None)
        .execution_options(synchronize_session=False)
    )
    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="release_claim",
            entity_type="ReviewQueueItem",
            entity_id="batch",
            details={"item_ids": list(item_ids)},
        )
    )
    await db.commit()
    return int(result.rowcount or 0)
