from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from dependencies.admin_auth import get_current_admin
from models.admin_control import AdminAccount
from models.user import User
from services.admin_moderation import (
    get_next_review_item,
    label_and_promote_to_gold,
    reject_review_item
)

router = APIRouter(prefix="/api/ctrl/moderation", tags=["control-moderation"])

class LabelRequest(BaseModel):
    corrected_transcript: str
    dialect: Optional[str] = None
    register: Optional[str] = None
    tags: list[str] = []
    audio_quality: float = 1.0
    noise_level: str = "low"
    notes: Optional[str] = None

class RejectionRequest(BaseModel):
    reason: str

@router.get("/next")
async def fetch_next_turn(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    item = await get_next_review_item(db)
    if not item:
        return {"item": None, "message": "Queue empty"}

    # Fetch teacher context
    teacher = await db.scalar(select(User).where(User.id == item.teacher_id))
    return {
        "item": {
            "id": item.id,
            "audio_url": item.source_audio_path,
            "transcript": item.source_transcript,
            "teacher_id": item.teacher_id,
            "teacher_hometown": teacher.hometown if teacher else "Unknown",
            "teacher_credibility": teacher.credibility_score if teacher else 0.0,
            "session_id": item.session_id,
            "extracted_claim": item.extracted_claim,
            "confidence": item.confidence,
            "timestamp": item.created_at
        }
    }

@router.post("/label/{item_id}")
async def submit_label(
    item_id: str,
    data: LabelRequest,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    try:
        gold = await label_and_promote_to_gold(
            db=db,
            item_id=item_id,
            admin=admin,
            corrected_transcript=data.corrected_transcript,
            dialect=data.dialect,
            register=data.register,
            tags=data.tags,
            audio_quality=data.audio_quality,
            noise_level=data.noise_level,
            notes=data.notes
        )
        return {"status": "success", "gold_record_id": gold.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/reject/{item_id}")
async def reject_turn(
    item_id: str,
    data: RejectionRequest,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    try:
        await reject_review_item(db, item_id, admin, data.reason)
        return {"status": "rejected"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
from sqlalchemy import select, func

@router.get("/gold")
async def list_gold_records(
    dialect: Optional[str] = None,
    quality_min: float = 0.0,
    page: int = 1,
    page_size: int = 50,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Searchable, paginated list of finalized training data.
    """
    stmt = select(GoldRecord).where(GoldRecord.audio_quality_score >= quality_min)
    if dialect:
        stmt = stmt.where(GoldRecord.dialect == dialect)
    
    # Sort by newest first
    stmt = stmt.order_by(GoldRecord.created_at.desc())
    
    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    # Simple count for pagination info
    count_stmt = select(func.count()).select_from(GoldRecord)
    if dialect:
        count_stmt = count_stmt.where(GoldRecord.dialect == dialect)
    
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()
    
    return {
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size
    }
