from __future__ import annotations

import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from models.intelligence import ReviewQueueItem
from models.message import Message
from models.dataset_gold import GoldRecord
from models.admin_control import AdminAuditLog, AdminAccount

logger = logging.getLogger("lipi.backend.admin.moderation")

async def get_next_review_item(db: AsyncSession) -> ReviewQueueItem | None:
    """Fetch the oldest pending review item."""
    result = await db.execute(
        select(ReviewQueueItem)
        .where(ReviewQueueItem.status == "pending_review")
        .order_by(ReviewQueueItem.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()

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
    notes: str | None = None
) -> GoldRecord:
    """
    Labels a review item, marks it as approved, and creates a GoldRecord.
    """
    item = await db.get(ReviewQueueItem, item_id)
    if not item:
        raise ValueError("Review item not found")

    # 1. Update Review Item status
    item.status = "approved"
    
    # 2. Extract context from original message if possible
    message = None
    if item.extraction_metadata.get("message_id"):
        # We assume the metadata stores the source message ID
        # If not, we might need a more complex join
        pass

    # 3. Create GoldRecord
    gold = GoldRecord(
        id=str(uuid.uuid4()),
        original_message_id=item.extraction_metadata.get("message_id"),
        session_id=item.session_id,
        teacher_id=item.teacher_id,
        audio_path=item.source_audio_path,
        raw_transcript=item.source_transcript or "",
        corrected_transcript=corrected_transcript,
        dialect=dialect,
        register=register,
        tags=tags or [],
        audio_quality_score=audio_quality,
        noise_level=noise_level,
        labeled_by=admin.id
    )
    db.add(gold)
    
    # 4. Audit Log
    audit = AdminAuditLog(
        admin_id=admin.id,
        action="approve_and_label",
        entity_type="GoldRecord",
        entity_id=gold.id,
        details={
            "review_item_id": item_id,
            "dialect": dialect,
            "tags": tags,
            "notes": notes
        }
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(gold)
    return gold

async def reject_review_item(
    db: AsyncSession,
    item_id: str,
    admin: AdminAccount,
    reason: str
):
    """Marks an item as rejected."""
    item = await db.get(ReviewQueueItem, item_id)
    if not item:
        raise ValueError("Review item not found")
        
    item.status = "rejected"
    
    audit = AdminAuditLog(
        admin_id=admin.id,
        action="reject_turn",
        entity_type="ReviewQueueItem",
        entity_id=item_id,
        details={"reason": reason}
    )
    db.add(audit)
    await db.commit()
