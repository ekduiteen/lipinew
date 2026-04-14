"""
Leaderboard API — < 50ms target via Valkey cache.

Cache strategy:
  - Key: leaderboard:{period}   TTL: 5 min
  - On cache miss: query DB, write cache, return
  - Period snapshots (weekly/monthly) are pre-built by the summary rebuild task
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cache import valkey
from db.connection import get_db
from dependencies.auth import get_current_user_optional
from models.points import TeacherPointsSummary
from models.user import User

router = APIRouter(prefix="/api", tags=["leaderboard"])
logger = logging.getLogger("lipi.backend.leaderboard")

Period = Literal["weekly", "monthly", "all_time"]
_CACHE_TTL = 300  # 5 minutes


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    points: int
    avatar_initial: str
    user_id: str


class LeaderboardResponse(BaseModel):
    period: str
    entries: list[LeaderboardEntry]
    cached: bool


async def _build_leaderboard(db: AsyncSession, period: Period) -> list[dict]:
    points_col = {
        "weekly":   TeacherPointsSummary.points_this_week,
        "monthly":  TeacherPointsSummary.points_this_month,
        "all_time": TeacherPointsSummary.total_points,
    }[period]

    rows = await db.execute(
        select(
            TeacherPointsSummary.teacher_id,
            points_col.label("points"),
            User.first_name,
        )
        .join(User, User.id == TeacherPointsSummary.teacher_id)
        .where(points_col > 0)
        .order_by(points_col.desc())
        .limit(100)
    )

    entries = []
    for rank, row in enumerate(rows, start=1):
        entries.append({
            "rank": rank,
            "name": row.first_name,
            "points": int(row.points),
            "avatar_initial": row.first_name[0].upper() if row.first_name else "?",
            "user_id": row.teacher_id,
        })
    return entries


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    period: Period = Query("weekly"),
    db: AsyncSession = Depends(get_db),
) -> list[LeaderboardEntry]:
    cache_key = f"leaderboard:{period}"

    # Try cache first
    cached = await valkey.get(cache_key)
    if cached:
        return [LeaderboardEntry(**e) for e in json.loads(cached)]

    # Cache miss — query DB
    entries = await _build_leaderboard(db, period)
    await valkey.setex(cache_key, _CACHE_TTL, json.dumps(entries))

    return [LeaderboardEntry(**e) for e in entries]


async def invalidate_leaderboard_cache() -> None:
    """Call after any points transaction to bust all period caches."""
    for period in ("weekly", "monthly", "all_time"):
        await valkey.delete(f"leaderboard:{period}")
