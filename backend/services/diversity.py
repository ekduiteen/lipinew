"""Global coverage scoring and update helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.curriculum import CurriculumPromptEvent, GlobalLanguageCoverage
from services.curriculum import TOPIC_TAXONOMY


async def load_gap_scores(
    db: AsyncSession,
    *,
    register_key: str,
    language_key: str,
) -> dict[tuple[str, str, str], float]:
    rows = await db.execute(
        select(GlobalLanguageCoverage).where(
            GlobalLanguageCoverage.register_key == register_key,
            GlobalLanguageCoverage.language_key == language_key,
        )
    )
    scores: dict[tuple[str, str, str], float] = {}
    for coverage in rows.scalars():
        key = (coverage.topic_key, coverage.register_key, coverage.language_key)
        scores[key] = score_topic_gap(
            coverage.coverage_score,
            coverage.unique_user_count,
            coverage.correction_density,
            coverage.topic_key,
        )

    for topic_key in TOPIC_TAXONOMY:
        key = (topic_key, register_key, language_key)
        scores.setdefault(key, 1.15 if TOPIC_TAXONOMY[topic_key].diversity_priority else 0.9)
    return scores


def score_topic_gap(
    coverage_score: float,
    unique_user_count: int,
    correction_density: float,
    topic_key: str,
) -> float:
    topic = TOPIC_TAXONOMY[topic_key]
    base = 1.0
    if topic.diversity_priority:
        base += 0.25
    base += max(0.0, 1.2 - min(coverage_score, 1.2))
    base += max(0.0, 0.8 - min(unique_user_count / 8.0, 0.8))
    base += min(correction_density, 1.0) * 0.35
    if topic_key == "everyday_basics":
        base -= 0.3
    return round(max(base, 0.1), 3)


async def _get_or_create_global_coverage(
    db: AsyncSession,
    *,
    topic_key: str,
    register_key: str,
    language_key: str,
) -> GlobalLanguageCoverage:
    row = await db.execute(
        select(GlobalLanguageCoverage).where(
            GlobalLanguageCoverage.topic_key == topic_key,
            GlobalLanguageCoverage.register_key == register_key,
            GlobalLanguageCoverage.language_key == language_key,
        )
    )
    coverage = row.scalar_one_or_none()
    if coverage:
        return coverage

    coverage = GlobalLanguageCoverage(
        id=str(uuid.uuid4()),
        topic_key=topic_key,
        register_key=register_key,
        language_key=language_key,
    )
    db.add(coverage)
    await db.flush()
    return coverage


async def refresh_global_coverage_for_event(
    db: AsyncSession,
    *,
    topic_key: str,
    register_key: str,
    language_key: str,
) -> GlobalLanguageCoverage:
    coverage = await _get_or_create_global_coverage(
        db,
        topic_key=topic_key,
        register_key=register_key,
        language_key=language_key,
    )

    answered_count = await db.scalar(
        select(func.count(CurriculumPromptEvent.id)).where(
            CurriculumPromptEvent.topic_key == topic_key,
            CurriculumPromptEvent.register_key == register_key,
            CurriculumPromptEvent.language_key == language_key,
            CurriculumPromptEvent.was_answered.is_(True),
        )
    )
    corrected_count = await db.scalar(
        select(func.count(CurriculumPromptEvent.id)).where(
            CurriculumPromptEvent.topic_key == topic_key,
            CurriculumPromptEvent.register_key == register_key,
            CurriculumPromptEvent.language_key == language_key,
            CurriculumPromptEvent.was_corrected.is_(True),
        )
    )
    unique_users = await db.scalar(
        select(func.count(distinct(CurriculumPromptEvent.user_id))).where(
            CurriculumPromptEvent.topic_key == topic_key,
            CurriculumPromptEvent.register_key == register_key,
            CurriculumPromptEvent.language_key == language_key,
            CurriculumPromptEvent.was_answered.is_(True),
        )
    )

    answered_value = int(answered_count or 0)
    corrected_value = int(corrected_count or 0)
    unique_user_value = int(unique_users or 0)
    coverage.coverage_score = round(answered_value + corrected_value * 1.5, 3)
    coverage.unique_user_count = unique_user_value
    coverage.correction_density = round(
        corrected_value / answered_value if answered_value else 0.0,
        3,
    )
    coverage.last_updated_at = datetime.now(timezone.utc)
    await db.flush()
    return coverage
