import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from dependencies.auth import get_current_user
from models.heritage import HeritageSession
from models.user import User
from services.heritage_prompt import generate_starter_prompt, generate_follow_up

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/heritage", tags=["heritage"])

class StartSessionRequest(BaseModel):
    mode: str

@router.post("/sessions/create")
async def create_session(
    req: StartSessionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        lang = getattr(user, "preferred_language", "nepali") or "nepali"
        prompt = await generate_starter_prompt(request.app.state.http, lang, req.mode)
        
        session_id = str(uuid.uuid4())
        h_session = HeritageSession(
            id=session_id,
            teacher_id=user.id,
            primary_language=lang,
            contribution_mode=req.mode,
            starter_prompt=prompt
        )
        db.add(h_session)
        await db.commit()
        await db.refresh(h_session)
        
        return {
            "session_id": h_session.id,
            "mode": h_session.contribution_mode,
            "starter_prompt": h_session.starter_prompt
        }
    except Exception as e:
        logger.error(f"Failed to start heritage session: {e}")
        raise HTTPException(status_code=500, detail="Could not create session")

@router.post("/sessions/{session_id}/submit_primary")
async def submit_primary(
    session_id: str,
    request: Request,
    text: str | None = Form(None),
    audio_file: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(HeritageSession).filter_by(id=session_id, teacher_id=user.id))
    h_session = result.scalar_one_or_none()
    if not h_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    audio_url = None
    if audio_file:
        audio_bytes = await audio_file.read()
        from services.audio_storage import store_phrase_audio
        audio_url = await store_phrase_audio(audio_bytes=audio_bytes, user_id=user.id, phrase_id=f"heritage-{session_id}")
        
    h_session.response_text = text or "[Audio Captured]"
    h_session.response_audio_url = audio_url
    
    # Generate follow up
    follow_up = await generate_follow_up(request.app.state.http, h_session.primary_language, h_session.contribution_mode, h_session.response_text)
    h_session.follow_up_prompt = follow_up
    
    await db.commit()
    
    return {
        "follow_up_prompt": follow_up
    }

@router.post("/sessions/{session_id}/submit_followup")
async def submit_followup(
    session_id: str,
    request: Request,
    text: str | None = Form(None),
    audio_file: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(HeritageSession).filter_by(id=session_id, teacher_id=user.id))
    h_session = result.scalar_one_or_none()
    if not h_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    audio_url = None
    if audio_file:
        audio_bytes = await audio_file.read()
        from services.audio_storage import store_phrase_audio
        audio_url = await store_phrase_audio(audio_bytes=audio_bytes, user_id=user.id, phrase_id=f"heritage-{session_id}-followup")
        
    h_session.follow_up_response_text = text or "[Audio Captured]"
    h_session.follow_up_response_audio = audio_url
    h_session.status = "completed"
    h_session.completed_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {"status": "completed"}
