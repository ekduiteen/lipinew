from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from dependencies.admin_auth import get_current_admin
from models.admin_control import AdminAccount
from models.dataset_gold import GoldRecord
from models.intelligence import KnowledgeConfidenceHistory, ReviewQueueItem, VocabularyEntry
from models.user import User
from services.admin_moderation import (
    CLAIM_TIMEOUT,
    ModerationFilters,
    batch_label_and_promote_to_gold,
    batch_reject_review_items,
    claim_review_buffer,
    claim_next_review_item,
    label_and_promote_to_gold,
    list_review_queue,
    reject_review_item,
    release_review_items,
)

router = APIRouter(prefix="/api/ctrl/moderation", tags=["control-moderation"])


class LabelRequest(BaseModel):
    corrected_transcript: str
    dialect: Optional[str] = None
    register_label: Optional[str] = Field(default=None, alias="register")
    tags: list[str] = Field(default_factory=list)
    audio_quality: float = 1.0
    noise_level: str = "low"
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class RejectionRequest(BaseModel):
    reason: str


class BatchApproveItem(BaseModel):
    id: str
    corrected_transcript: Optional[str] = None
    dialect: Optional[str] = None
    register_label: Optional[str] = Field(default=None, alias="register")
    tags: list[str] = Field(default_factory=list)
    audio_quality: float = 1.0
    noise_level: str = "low"
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class BatchApproveRequest(BaseModel):
    items: list[BatchApproveItem]


class BatchRejectRequest(BaseModel):
    ids: list[str]
    reason: str


class BatchSkipRequest(BaseModel):
    ids: list[str]


def _build_filters(
    *,
    review_type: str | None,
    language: str | None,
    confidence_min: float | None,
    confidence_max: float | None,
    source: str | None,
    age: str,
    claimed: str = "all",
) -> ModerationFilters:
    return ModerationFilters(
        review_type=review_type or None,
        language=language or None,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        source=source or None,
        age_order=age,
        claimed=claimed,
    )


def _derive_review_type(item: ReviewQueueItem) -> str:
    metadata = item.extraction_metadata or {}
    if metadata.get("review_kind") == "low_trust_extraction":
        return "low_trust_extraction"
    if metadata.get("correction_event_id"):
        return "correction"
    return "generic_review"


def _derive_source_type(item: ReviewQueueItem) -> str:
    return "human" if _derive_review_type(item) == "correction" else "model"


async def _supporting_teacher_count(
    db: AsyncSession,
    *,
    word: str,
    language: str,
) -> int:
    row = await db.execute(
        select(VocabularyEntry.distinct_teacher_count).where(
            VocabularyEntry.word == word,
            VocabularyEntry.language == language,
        )
    )
    return int(row.scalar() or 0)


async def _serialize_review_item(db: AsyncSession, item: ReviewQueueItem) -> dict:
    teacher = None
    if item.teacher_id:
        teacher = await db.scalar(select(User).where(User.id == item.teacher_id))

    metadata = item.extraction_metadata or {}
    language_key = str(metadata.get("language_key") or "unknown")
    supporting_teachers = await _supporting_teacher_count(
        db,
        word=item.extracted_claim or "",
        language=language_key if language_key != "unknown" else "ne",
    )
    claim_expires_at = (
        item.claimed_at + CLAIM_TIMEOUT if item.claimed_at is not None else None
    )

    return {
        "id": item.id,
        "audio_url": item.source_audio_path,
        "transcript": item.source_transcript,
        "teacher_id": item.teacher_id,
        "teacher_hometown": teacher.hometown if teacher else "Unknown",
        "teacher_credibility": teacher.credibility_score if teacher else 0.0,
        "session_id": item.session_id,
        "extracted_claim": item.extracted_claim,
        "confidence": item.confidence,
        "timestamp": item.created_at,
        "review_type": _derive_review_type(item),
        "source_type": _derive_source_type(item),
        "language_key": language_key,
        "model_source": item.model_source,
        "claimed_by": item.claimed_by,
        "claimed_at": item.claimed_at,
        "claim_expires_at": claim_expires_at,
        "supporting_teacher_count": supporting_teachers,
        "metadata": metadata,
    }


@router.get("/next")
async def fetch_next_turn(
    review_type: str | None = Query(default=None),
    language: str | None = Query(default=None),
    confidence_min: float | None = Query(default=None),
    confidence_max: float | None = Query(default=None),
    source: str | None = Query(default=None),
    age: str = Query(default="oldest", pattern="^(oldest|newest)$"),
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = _build_filters(
        review_type=review_type,
        language=language,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        source=source,
        age=age,
    )
    item = await claim_next_review_item(db, admin=admin, filters=filters)
    if not item:
        return {"item": None, "message": "Queue empty"}
    return {"item": await _serialize_review_item(db, item)}


@router.get("/queue")
async def list_queue(
    review_type: str | None = Query(default=None),
    language: str | None = Query(default=None),
    confidence_min: float | None = Query(default=None),
    confidence_max: float | None = Query(default=None),
    source: str | None = Query(default=None),
    age: str = Query(default="oldest", pattern="^(oldest|newest)$"),
    claimed: str = Query(default="all", pattern="^(all|mine|unclaimed)$"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = _build_filters(
        review_type=review_type,
        language=language,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        source=source,
        age=age,
        claimed=claimed,
    )
    items, total = await list_review_queue(
        db,
        admin=admin,
        filters=filters,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [await _serialize_review_item(db, item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/claim-buffer")
async def claim_buffer(
    review_type: str | None = Query(default=None),
    language: str | None = Query(default=None),
    confidence_min: float | None = Query(default=None),
    confidence_max: float | None = Query(default=None),
    source: str | None = Query(default=None),
    age: str = Query(default="oldest", pattern="^(oldest|newest)$"),
    limit: int = Query(default=3, ge=1, le=10),
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = _build_filters(
        review_type=review_type,
        language=language,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        source=source,
        age=age,
    )
    items = await claim_review_buffer(db, admin=admin, filters=filters, limit=limit)
    return {"items": [await _serialize_review_item(db, item) for item in items]}


@router.post("/label/{item_id}")
async def submit_label(
    item_id: str,
    data: LabelRequest,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        gold = await label_and_promote_to_gold(
            db=db,
            item_id=item_id,
            admin=admin,
            corrected_transcript=data.corrected_transcript,
            dialect=data.dialect,
            register=data.register_label,
            tags=data.tags,
            audio_quality=data.audio_quality,
            noise_level=data.noise_level,
            notes=data.notes,
        )
        return {"status": "success", "gold_record_id": gold.id}
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/batch/approve")
async def submit_batch_label(
    data: BatchApproveRequest,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        gold_records = await batch_label_and_promote_to_gold(
            db,
            item_specs=[item.model_dump() for item in data.items],
            admin=admin,
        )
        return {
            "status": "success",
            "approved_count": len(gold_records),
            "gold_record_ids": [gold.id for gold in gold_records],
        }
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/reject/{item_id}")
async def reject_turn(
    item_id: str,
    data: RejectionRequest,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        await reject_review_item(db, item_id, admin, data.reason)
        return {"status": "rejected"}
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/batch/reject")
async def reject_batch(
    data: BatchRejectRequest,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        rejected = await batch_reject_review_items(
            db,
            item_ids=data.ids,
            admin=admin,
            reason=data.reason,
        )
        return {"status": "rejected", "rejected_count": rejected}
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/batch/skip")
async def skip_batch(
    data: BatchSkipRequest,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    released = await release_review_items(db, item_ids=data.ids, admin=admin)
    return {"status": "released", "released_count": released}


@router.get("/gold")
async def list_gold_records(
    dialect: Optional[str] = None,
    language: Optional[str] = None,
    quality_min: float = 0.0,
    page: int = 1,
    page_size: int = 50,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(GoldRecord).where(GoldRecord.audio_quality_score >= quality_min)
    if dialect:
        stmt = stmt.where(GoldRecord.dialect == dialect)
    if language:
        stmt = stmt.where(GoldRecord.primary_language == language)

    stmt = stmt.order_by(GoldRecord.created_at.desc())
    offset = (page - 1) * page_size
    rows = await db.execute(stmt.offset(offset).limit(page_size))
    records = list(rows.scalars())

    count_stmt = select(func.count()).select_from(GoldRecord).where(GoldRecord.audio_quality_score >= quality_min)
    if dialect:
        count_stmt = count_stmt.where(GoldRecord.dialect == dialect)
    if language:
        count_stmt = count_stmt.where(GoldRecord.primary_language == language)
    total = int((await db.execute(count_stmt)).scalar() or 0)

    payload = []
    for rec in records:
        history_rows = (
            await db.execute(
                select(KnowledgeConfidenceHistory)
                .where(
                    KnowledgeConfidenceHistory.teacher_id == rec.teacher_id,
                    KnowledgeConfidenceHistory.session_id == rec.session_id,
                    KnowledgeConfidenceHistory.knowledge_key == rec.corrected_transcript,
                )
                .order_by(KnowledgeConfidenceHistory.created_at.desc())
                .limit(3)
            )
        ).scalars().all()
        payload.append(
            {
                "id": rec.id,
                "corrected_transcript": rec.corrected_transcript,
                "raw_transcript": rec.raw_transcript,
                "dialect": rec.dialect,
                "register": rec.register,
                "primary_language": rec.primary_language,
                "audio_quality_score": rec.audio_quality_score,
                "noise_level": rec.noise_level,
                "created_at": rec.created_at,
                "tags": rec.tags,
                "provenance": {
                    "original_message_id": rec.original_message_id,
                    "session_id": rec.session_id,
                    "teacher_id": rec.teacher_id,
                    "labeled_by": rec.labeled_by,
                },
                "confidence_history": [
                    {
                        "change_reason": row.change_reason,
                        "previous_confidence": row.previous_confidence,
                        "new_confidence": row.new_confidence,
                        "created_at": row.created_at,
                    }
                    for row in history_rows
                ],
            }
        )

    return {
        "records": payload,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
