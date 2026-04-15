"""
Teacher routes — onboarding, stats, tone profile.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from dependencies.auth import get_current_user
from models.user import User
from models.points import TeacherPointsSummary
from models.badge import TeacherBadge, Badge
from services.points import rebuild_summary
from cache import valkey

router = APIRouter(prefix="/api/teachers", tags=["teachers"])
logger = logging.getLogger("lipi.backend.teachers")

_PROFILE_KEY = "user:{user_id}:tone_profile"


# ─── Schemas ─────────────────────────────────────────────────────────────────

class OnboardingPayload(BaseModel):
    first_name: str
    last_name: str
    age: int
    native_language: str
    other_languages: list[str] = []
    gender: str
    city_or_village: str
    education_level: str
    audio_consent: bool = False


class TeacherStatsResponse(BaseModel):
    total_points: int
    weekly_points: int
    monthly_points: int
    current_streak: int
    longest_streak: int
    sessions_completed: int
    words_taught: int
    rank: int


class BadgeResponse(BaseModel):
    id: str
    name: str
    icon: str
    description_ne: str
    description_en: str
    awarded_at: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/onboarding", status_code=201)
async def complete_onboarding(
    payload: OnboardingPayload,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.first_name = payload.first_name
    user.last_name = payload.last_name
    user.age = payload.age
    user.primary_language = payload.native_language
    user.other_languages = payload.other_languages
    user.gender = payload.gender
    user.hometown = payload.city_or_village
    user.education_level = payload.education_level
    user.consent_audio_training = payload.audio_consent
    user.onboarding_complete = True

    # Derive default register from age
    if payload.age >= 60:
        register = "hajur"
    elif payload.age >= 30:
        register = "tapai"
    else:
        register = "timi"

    # Build tone profile and cache it
    tone_profile = {
        "name": f"{payload.first_name} {payload.last_name}".strip(),
        "age": payload.age,
        "gender": payload.gender,
        "native_language": payload.native_language,
        "other_languages": payload.other_languages,
        "city_or_village": payload.city_or_village,
        "register": register,
        "energy_level": 3,
        "humor_level": 3,
        "code_switch_ratio": 0.2,
        "session_phase": 1,
        "previous_topics": [],
        "preferred_topics": (
            ["regional_variation", "culture_ritual"]
            if payload.native_language.lower() in {"newar", "newari", "nepal bhasa", "newa"}
            else []
        ),
    }
    await valkey.setex(
        _PROFILE_KEY.format(user_id=user_id),
        86400,  # 24h
        json.dumps(tone_profile),
    )

    await db.commit()
    return {"user_id": user_id, "register": register}


@router.get("/me/stats", response_model=TeacherStatsResponse)
async def get_my_stats(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeacherStatsResponse:
    summary = await db.get(TeacherPointsSummary, user_id)
    if not summary:
        # First visit — create empty summary
        summary = await rebuild_summary(db, user_id)
        await db.commit()

    # Compute rank from leaderboard cache
    cached = await valkey.get("leaderboard:all_time")
    rank = 0
    if cached:
        entries = json.loads(cached)
        for e in entries:
            if e["user_id"] == user_id:
                rank = e["rank"]
                break

    return TeacherStatsResponse(
        total_points=summary.total_points,
        weekly_points=summary.points_this_week,
        monthly_points=summary.points_this_month,
        current_streak=summary.current_streak_days,
        longest_streak=summary.longest_streak_days,
        sessions_completed=summary.total_sessions,
        words_taught=summary.total_words_taught,
        rank=rank,
    )


@router.get("/me/badges", response_model=list[BadgeResponse])
async def get_my_badges(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BadgeResponse]:
    from sqlalchemy import select
    rows = await db.execute(
        select(TeacherBadge, Badge)
        .join(Badge, Badge.id == TeacherBadge.badge_id)
        .where(TeacherBadge.teacher_id == user_id)
        .order_by(TeacherBadge.earned_at.desc())
    )
    return [
        BadgeResponse(
            id=badge.id,
            name=badge.name_english,
            icon=badge.icon_emoji,
            description_ne=badge.description_ne,
            description_en=badge.description_en,
            awarded_at=tb.awarded_at.isoformat(),
        )
        for tb, badge in rows
    ]
