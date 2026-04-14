"""
Points calculation and immutable transaction logging.
All values from GAMIFICATION_DATA_MODEL.md / CLAUDE.md.

Rules:
  - Never update or delete points_transactions rows
  - Calculate final_points = floor(base_points * multiplier)
  - Streak multipliers stack with event multipliers by taking the max
"""

from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.points import PointsTransaction, TeacherPointsSummary

# ─── Point values ────────────────────────────────────────────────────────────

POINT_VALUES: dict[str, int] = {
    "session_base":         10,
    "word_learned":          5,
    "correction_accepted":  15,
    "audio_quality":         2,
    "pioneer_word":         25,
    "milestone_bonus":      50,
}

MULTIPLIERS: dict[str, float] = {
    "streak_7_days":      2.0,
    "streak_30_days":     3.0,
    "streak_100_days":    5.0,
    "rare_dialect":       3.0,
    "minority_language":  2.0,
}

# Streak day thresholds → multiplier
_STREAK_TIERS = [(100, 5.0), (30, 3.0), (7, 2.0)]


def streak_multiplier(current_streak: int) -> float:
    for days, mult in _STREAK_TIERS:
        if current_streak >= days:
            return mult
    return 1.0


def calculate_points(
    event_type: str,
    current_streak: int = 0,
    extra_multiplier: float = 1.0,
) -> tuple[int, float, int]:
    """Returns (base_points, multiplier, final_points)."""
    base = POINT_VALUES.get(event_type, 0)
    mult = max(streak_multiplier(current_streak), extra_multiplier)
    final = math.floor(base * mult)
    return base, mult, final


# ─── DB operations ───────────────────────────────────────────────────────────

async def log_transaction(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str | None,
    event_type: str,
    current_streak: int = 0,
    extra_multiplier: float = 1.0,
    meta: dict | None = None,
) -> PointsTransaction:
    """Append an immutable points event. Never call UPDATE on this table."""
    base, mult, final = calculate_points(event_type, current_streak, extra_multiplier)

    tx = PointsTransaction(
        id=str(uuid.uuid4()),
        teacher_id=user_id,
        session_id=session_id,
        event_type=event_type,
        base_points=base,
        multiplier=mult,
        final_points=final,
        context=meta,
        validated=True,
        validation_method="auto",
    )
    db.add(tx)
    await db.flush()
    return tx


async def get_current_streak(db: AsyncSession, user_id: str) -> int:
    """Read streak from summary table (rebuilt every 5 min by background task)."""
    result = await db.execute(
        select(TeacherPointsSummary.current_streak_days).where(
            TeacherPointsSummary.teacher_id == user_id
        )
    )
    row = result.scalar_one_or_none()
    return row or 0


async def rebuild_summary(db: AsyncSession, user_id: str) -> TeacherPointsSummary:
    """
    Recompute the summary row from the raw transaction log.
    Called by the 5-minute background task; also callable on-demand after session end.
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)

    week_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    month_dt = datetime.combine(month_start, datetime.min.time()).replace(tzinfo=timezone.utc)

    # Total points
    total_q = await db.execute(
        select(func.coalesce(func.sum(PointsTransaction.final_points), 0)).where(
            PointsTransaction.teacher_id == user_id
        )
    )
    total = int(total_q.scalar())

    # Weekly points
    weekly_q = await db.execute(
        select(func.coalesce(func.sum(PointsTransaction.final_points), 0)).where(
            PointsTransaction.teacher_id == user_id,
            PointsTransaction.created_at >= week_dt,
        )
    )
    weekly = int(weekly_q.scalar())

    # Monthly points
    monthly_q = await db.execute(
        select(func.coalesce(func.sum(PointsTransaction.final_points), 0)).where(
            PointsTransaction.teacher_id == user_id,
            PointsTransaction.created_at >= month_dt,
        )
    )
    monthly = int(monthly_q.scalar())

    # Session count
    sessions_q = await db.execute(
        select(func.count()).where(
            PointsTransaction.teacher_id == user_id,
            PointsTransaction.event_type == "session_base",
        )
    )
    sessions = int(sessions_q.scalar())

    # Words taught
    words_q = await db.execute(
        select(func.count()).where(
            PointsTransaction.teacher_id == user_id,
            PointsTransaction.event_type == "word_learned",
        )
    )
    words = int(words_q.scalar())

    # Upsert summary
    existing = await db.get(TeacherPointsSummary, user_id)
    if existing:
        existing.total_points = total
        existing.points_this_week = weekly
        existing.points_this_month = monthly
        existing.total_sessions = sessions
        existing.total_words_taught = words
        existing.week_start = week_start
        existing.month_start = month_start
        existing.last_rebuilt = now
        summary = existing
    else:
        summary = TeacherPointsSummary(
            teacher_id=user_id,
            total_points=total,
            points_this_week=weekly,
            points_this_month=monthly,
            total_sessions=sessions,
            total_words_taught=words,
            week_start=week_start,
            month_start=month_start,
            last_rebuilt=now,
        )
        db.add(summary)

    await db.flush()
    return summary
