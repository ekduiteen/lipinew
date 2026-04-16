from fastapi import APIRouter, Depends, Form, UploadFile, File, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import select
import uuid

from db.connection import get_db
from dependencies.auth import get_current_user
from services.phrase_pipeline import get_next_phrase, process_phrase_audio
from services.audio_storage import store_phrase_audio
from models.phrases import PhraseSkipEvent, Phrase, PhraseGenerationBatch
import logging

router = APIRouter()
logger = logging.getLogger("lipi.backend.phrases")

@router.get("/api/phrases/next")
async def fetch_next_phrase(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    phrase = await get_next_phrase(db, user_id)
    if not phrase:
        # Fallback if db is completely empty
        return {"id": None, "text_en": "You're all out of phrases!", "text_ne": "तपाईंले सबै वाक्यांशहरू सक्नुभयो!"}
    
    return {
        "id": phrase.id,
        "text_en": phrase.text_en,
        "text_ne": phrase.text_ne,
        "category": phrase.category
    }

@router.post("/api/phrases/submit-audio")
async def submit_audio(
    request: Request,
    phrase_id: str = Form(...),
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    audio_bytes = await audio_file.read()
    
    # Store audio
    uri = await store_phrase_audio(
        audio_bytes=audio_bytes, 
        user_id=user_id, 
        phrase_id=phrase_id
    )
    
    # Process
    http = request.app.state.http
    result = await process_phrase_audio(
        db=db,
        http=http,
        user_id=user_id,
        phrase_id=phrase_id,
        audio_bytes=audio_bytes,
        audio_uri=uri,
        submission_role="primary"
    )
    
    if result["status"] == "success":
        await db.commit()
    else:
        await db.rollback() # Don't commit poor audio to core paths
    
    return result

@router.post("/api/phrases/submit-variation-audio")
async def submit_variation_audio(
    request: Request,
    phrase_id: str = Form(...),
    group_id: str = Form(...),
    variation_type: str = Form(...),
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    audio_bytes = await audio_file.read()
    
    uri = await store_phrase_audio(
        audio_bytes=audio_bytes, 
        user_id=user_id, 
        phrase_id=phrase_id,
        suffix=f"var-{variation_type}"
    )
    
    http = request.app.state.http
    result = await process_phrase_audio(
        db=db,
        http=http,
        user_id=user_id,
        phrase_id=phrase_id,
        audio_bytes=audio_bytes,
        audio_uri=uri,
        submission_role="variation",
        variation_type=variation_type,
        group_id=group_id
    )
    
    if result["status"] == "success":
        await db.commit()
    else:
        await db.rollback()
        
    return result

@router.post("/api/phrases/skip")
async def skip_phrase(
    phrase_id: str = Form(...),
    reason: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    db.add(PhraseSkipEvent(
        phrase_id=phrase_id,
        user_id=user_id,
        reason_optional=reason
    ))
    await db.commit()
    
    # Auto fetch next
    return await fetch_next_phrase(db, user_id)


# Admin routes (placeholder/minimal for Generation and Review)

@router.post("/api/phrases/generate")
async def generate_phrases(
    category: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    # Security note: A real implementation would verify `user_id` is an Admin role.
    batch = PhraseGenerationBatch(
        generator_model="gemma-3-audio",
        generation_prompt=f"Generate phrases for {category}",
        category=category
    )
    db.add(batch)
    await db.commit()
    return {"status": "batch_created", "batch_id": batch.id}

@router.post("/api/phrases/review/{phrase_id}")
async def review_phrase(
    phrase_id: str,
    action: str = Form(...), # approved, rejected
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    phrase = await db.get(Phrase, phrase_id)
    if not phrase:
        raise HTTPException(404, "Phrase not found")
        
    if action == "approved":
        phrase.review_status = "approved"
        phrase.is_active = True
    elif action == "rejected":
        phrase.review_status = "rejected"
        phrase.is_active = False
        
    await db.commit()
    return {"status": "ok", "new_status": phrase.review_status}
