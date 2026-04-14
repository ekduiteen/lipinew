"""
Badge award system.
Checks are idempotent — safe to call after every session.
Never re-awards an already-held badge.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.badge import Badge, TeacherBadge
from models.points import TeacherPointsSummary

logger = logging.getLogger("lipi.backend.badges")


@dataclass
class BadgeAward:
    badge_id: str
    name: str
    icon: str
    description_ne: str
    description_en: str


async def check_and_award(
    db: AsyncSession,
    user_id: str,
) -> list[BadgeAward]:
    """
    Check all badge thresholds against the teacher's summary.
    Returns newly awarded badges (empty list if nothing new).
    """
    summary = await db.get(TeacherPointsSummary, user_id)
    if not summary:
        return []

    # Badges the teacher already holds
    existing_q = await db.execute(
        select(TeacherBadge.badge_id).where(TeacherBadge.teacher_id == user_id)
    )
    already_held = {row for (row,) in existing_q}

    # All badge definitions
    all_badges_q = await db.execute(select(Badge))
    all_badges: list[Badge] = list(all_badges_q.scalars())

    newly_awarded: list[BadgeAward] = []

    for badge in all_badges:
        if badge.id in already_held:
            continue

        if not badge.is_active:
            continue

        earned = False
        tv = badge.trigger_value or 0
        match badge.trigger_type:
            case "words_taught":
                earned = summary.total_words_taught >= tv
            case "streak_days":
                earned = summary.current_streak_days >= tv
            case "corrections_made":
                earned = summary.total_corrections >= tv
            case "pioneer":
                # Awarded by learning.py when a pioneer word is taught — skip here
                earned = False

        if earned:
            db.add(TeacherBadge(
                id=str(uuid.uuid4()),
                teacher_id=user_id,
                badge_id=badge.id,
            ))
            newly_awarded.append(BadgeAward(
                badge_id=badge.id,
                name=badge.name_english,
                icon=badge.icon_emoji,
                description_ne=badge.description_ne,
                description_en=badge.description_en,
            ))
            logger.info("Badge awarded user=%s badge=%s", user_id, badge.id)

    if newly_awarded:
        await db.flush()

    return newly_awarded
