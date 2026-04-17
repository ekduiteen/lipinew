from __future__ import annotations

import json
import asyncio
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cache import valkey
from config import settings
from db.connection import get_db
from dependencies.admin_auth import get_current_admin
from models.admin_control import AdminAccount, AdminAuditLog
from models.dataset_gold import GoldRecord
from models.intelligence import ReviewQueueItem
from models.message import Message
from services.admin_moderation import claim_expiry_cutoff
from services.audio_storage import _build_client

router = APIRouter(prefix="/api/ctrl/system", tags=["control-system"])


def _today_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


async def _compute_real_metrics(db: AsyncSession) -> dict:
    pending_queue_size = int(
        await db.scalar(
            select(func.count())
            .select_from(ReviewQueueItem)
            .where(ReviewQueueItem.status == "pending_review")
        )
        or 0
    )
    items_claimed = int(
        await db.scalar(
            select(func.count())
            .select_from(ReviewQueueItem)
            .where(
                ReviewQueueItem.status == "pending_review",
                ReviewQueueItem.claimed_by.is_not(None),
                ReviewQueueItem.claimed_at.is_not(None),
                ReviewQueueItem.claimed_at >= claim_expiry_cutoff(),
            )
        )
        or 0
    )

    day_start = _today_start()
    approvals_today = int(
        await db.scalar(
            select(func.count())
            .select_from(AdminAuditLog)
            .where(
                AdminAuditLog.action == "approve_and_label",
                AdminAuditLog.created_at >= day_start,
            )
        )
        or 0
    )
    rejections_today = int(
        await db.scalar(
            select(func.count())
            .select_from(AdminAuditLog)
            .where(
                AdminAuditLog.action == "reject_turn",
                AdminAuditLog.created_at >= day_start,
            )
        )
        or 0
    )
    gold_records_created = int(await db.scalar(select(func.count()).select_from(GoldRecord)) or 0)

    review_items = (
        await db.execute(
            select(ReviewQueueItem.extraction_metadata, ReviewQueueItem.created_at, ReviewQueueItem.updated_at)
        )
    ).all()
    low_trust_count = 0
    review_durations: list[float] = []
    for metadata, created_at, updated_at in review_items:
        if (metadata or {}).get("review_kind") == "low_trust_extraction":
            low_trust_count += 1
        if created_at and updated_at and updated_at > created_at:
            review_durations.append((updated_at - created_at).total_seconds())

    total_review_items = len(review_items)
    low_trust_rate = (low_trust_count / total_review_items) if total_review_items else 0.0
    avg_review_time_seconds = (
        round(sum(review_durations) / len(review_durations), 2) if review_durations else 0.0
    )

    total_raw = int(await db.scalar(select(func.count()).select_from(Message)) or 0)
    yield_percentage = (gold_records_created / total_raw * 100.0) if total_raw else 0.0

    return {
        "pending_queue_size": pending_queue_size,
        "items_claimed": items_claimed,
        "approvals_today": approvals_today,
        "rejections_today": rejections_today,
        "low_trust_rate": round(low_trust_rate, 4),
        "gold_records_created": gold_records_created,
        "avg_review_time_seconds": avg_review_time_seconds,
        "raw_capture": total_raw,
        "yield_percentage": round(yield_percentage, 2),
    }


async def _check_minio_health() -> bool:
    try:
        client = _build_client()
        return await asyncio.to_thread(
            client.bucket_exists,
            settings.minio_bucket_audio,
        )
    except Exception:
        return False


@router.get("/health")
async def get_system_health(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    gold_count = int(await db.scalar(select(func.count()).select_from(GoldRecord)) or 0)
    raw_count = int(await db.scalar(select(func.count()).select_from(Message)) or 0)

    valkey_ok = False
    try:
        await valkey.ping()
        valkey_ok = True
    except Exception:
        valkey_ok = False

    minio_ok = await _check_minio_health()

    return {
        "status": "healthy" if valkey_ok and minio_ok else "degraded",
        "counts": {
            "gold_records": gold_count,
            "raw_messages": raw_count,
        },
        "services": {
            "database": True,
            "valkey": valkey_ok,
            "storage": minio_ok,
        },
        "config": {
            "environment": settings.environment,
            "ml_service_url": settings.ml_service_url,
        },
    }


@router.get("/audit")
async def get_audit_overview(
    limit: int = 50,
    offset: int = 0,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(AdminAuditLog, AdminAccount.full_name)
        .join(AdminAccount, AdminAuditLog.admin_id == AdminAccount.id, isouter=True)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    logs = []
    for log, admin_name in result.all():
        logs.append(
            {
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_name": admin_name or "System",
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "details": log.details,
                "created_at": log.created_at,
            }
        )

    total = int(await db.scalar(select(func.count()).select_from(AdminAuditLog)) or 0)
    return {"logs": logs, "total": total}


@router.get("/metrics/real")
async def get_real_metrics(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _compute_real_metrics(db)


@router.get("/stats/summary")
async def get_stats_summary(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    metrics = await _compute_real_metrics(db)
    return {
        **metrics,
        "pending_review": metrics["pending_queue_size"],
        "gold_yield": metrics["gold_records_created"],
    }


@router.get("/stats/timeseries")
async def get_stats_timeseries(
    days: int = 30,
    dialect: str | None = None,
    register: str | None = None,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"ctrl:stats:ts:{days}:{dialect or 'all'}:{register or 'all'}"
    cached_val = await valkey.get(cache_key)
    if cached_val:
        return json.loads(cached_val)

    from models.session import TeachingSession

    gold_stmt = (
        select(
            func.date_trunc("day", GoldRecord.created_at).label("day"),
            func.count(GoldRecord.id).label("count"),
        )
    )
    if dialect:
        gold_stmt = gold_stmt.where(GoldRecord.dialect == dialect)
    if register:
        gold_stmt = gold_stmt.where(GoldRecord.register == register)
    gold_stmt = gold_stmt.group_by("day").order_by("day").limit(days)

    raw_stmt = (
        select(
            func.date_trunc("day", Message.created_at).label("day"),
            func.count(Message.id).label("count"),
        )
    )
    if register:
        raw_stmt = raw_stmt.join(TeachingSession, Message.session_id == TeachingSession.id)
        raw_stmt = raw_stmt.where(TeachingSession.register_used == register)
    raw_stmt = raw_stmt.group_by("day").order_by("day").limit(days)

    gold_res = await db.execute(gold_stmt)
    raw_res = await db.execute(raw_stmt)

    data_map: dict[str, dict] = {}
    for day, count in gold_res.all():
        d_str = day.strftime("%Y-%m-%d")
        data_map[d_str] = {"date": d_str, "gold": count, "raw": 0}
    for day, count in raw_res.all():
        d_str = day.strftime("%Y-%m-%d")
        if d_str in data_map:
            data_map[d_str]["raw"] = count
        else:
            data_map[d_str] = {"date": d_str, "gold": 0, "raw": count}

    final_data = sorted(data_map.values(), key=lambda row: row["date"])
    await valkey.setex(cache_key, 900, json.dumps(final_data))
    return final_data
