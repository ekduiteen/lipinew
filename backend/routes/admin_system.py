from __future__ import annotations

import json
import uuid
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from cache import valkey
from config import settings
from db.connection import get_db
from dependencies.admin_auth import get_current_admin
from models.admin_control import AdminAccount, AdminAuditLog
from models.dataset_gold import GoldRecord
from models.intelligence import AdminKeytermSeed, ReviewQueueItem
from models.message import Message
from models.session import TeachingSession
from services.admin_moderation import claim_expiry_cutoff
from services.audio_storage import check_bucket_health

router = APIRouter(prefix="/api/ctrl/system", tags=["control-system"])


class KeytermSeedCreate(BaseModel):
    seed_text: str = Field(..., min_length=1, max_length=500)
    language_key: str = Field("ne", max_length=20)
    entity_type: str = Field("vocabulary", pattern=r"^(vocabulary|proper_name|phrase|honorific_or_register_term|language_name|pronunciation_target|cultural_concept|corrected_term)$")
    domain_key: str | None = None
    weight: float = Field(1.0, ge=0.0, le=10.0)
    source_note: str | None = Field(None, max_length=500)
    is_active: bool = True


def _today_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    return bool(
        await db.scalar(
            text("SELECT to_regclass(:table_name) IS NOT NULL"),
            {"table_name": f"public.{table_name}"},
        )
    )


async def _safe_count(db: AsyncSession, table_name: str, stmt) -> int:
    if not await _table_exists(db, table_name):
        return 0
    try:
        return int(await db.scalar(stmt) or 0)
    except ProgrammingError:
        return 0


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
    gold_records_created = await _safe_count(
        db,
        "dataset_gold_records",
        select(func.count()).select_from(GoldRecord),
    )

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
    return await check_bucket_health()


@router.get("/health")
async def get_system_health(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    gold_count = await _safe_count(
        db,
        "dataset_gold_records",
        select(func.count()).select_from(GoldRecord),
    )
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

    if await _table_exists(db, "dataset_gold_records"):
        gold_res = await db.execute(gold_stmt)
        gold_rows = gold_res.all()
    else:
        gold_rows = []
    raw_res = await db.execute(raw_stmt)

    data_map: dict[str, dict] = {}
    for day, count in gold_rows:
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


@router.get("/keyterm-seeds")
async def list_keyterm_seeds(
    language: str | None = None,
    active_only: bool = True,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AdminKeytermSeed).order_by(AdminKeytermSeed.weight.desc(), AdminKeytermSeed.created_at.desc())
    if language:
        stmt = stmt.where(AdminKeytermSeed.language_key == language)
    if active_only:
        stmt = stmt.where(AdminKeytermSeed.is_active.is_(True))
    rows = (await db.execute(stmt.limit(200))).scalars().all()
    return {
        "seeds": [
            {
                "id": row.id,
                "language_key": row.language_key,
                "seed_text": row.seed_text,
                "normalized_text": row.normalized_text,
                "entity_type": row.entity_type,
                "domain_key": row.domain_key,
                "weight": row.weight,
                "source_note": row.source_note,
                "is_active": row.is_active,
            }
            for row in rows
        ]
    }


@router.post("/keyterm-seeds")
async def create_keyterm_seed(
    payload: KeytermSeedCreate,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    seed_text = payload.seed_text.strip()
    normalized = " ".join(seed_text.lower().split())
    row = AdminKeytermSeed(
        id=str(uuid.uuid4()),
        language_key=payload.language_key,
        seed_text=seed_text,
        normalized_text=normalized,
        entity_type=payload.entity_type,
        domain_key=payload.domain_key,
        weight=payload.weight,
        source_note=payload.source_note,
        is_active=payload.is_active,
        created_by=admin.id,
    )
    db.add(row)
    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="create_keyterm_seed",
            entity_type="AdminKeytermSeed",
            entity_id=row.id,
            details={
                "seed_text": seed_text,
                "language_key": row.language_key,
                "entity_type": row.entity_type,
            },
        )
    )
    await db.commit()
    return {"status": "ok", "id": row.id}


@router.get("/intelligence/overview")
async def get_turn_intelligence_overview(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if await _table_exists(db, "message_analysis"):
        overview = await db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS analysis_count,
                    SUM(CASE WHEN intent_label = 'correction' THEN 1 ELSE 0 END) AS correction_count,
                    SUM(CASE WHEN intent_label = 'casual_chat' THEN 1 ELSE 0 END) AS casual_count,
                    SUM(CASE WHEN intent_label = 'low_signal' THEN 1 ELSE 0 END) AS low_signal_count
                FROM message_analysis
                """
            )
        )
        row = overview.one()
        recent_rows = await db.execute(
            text(
                """
                SELECT transcript_final, intent_label, intent_confidence, primary_language, keyterms_json, quality_json
                FROM message_analysis
                ORDER BY created_at DESC
                LIMIT 20
                """
            )
        )
    else:
        row = type("Row", (), {
            "analysis_count": 0,
            "correction_count": 0,
            "casual_count": 0,
            "low_signal_count": 0,
        })()
        recent_rows = []

    if await _table_exists(db, "message_entities"):
        entity_rows = await db.execute(
            text(
                """
                SELECT language, entity_type, normalized_text, confidence
                FROM message_entities
                ORDER BY created_at DESC
                LIMIT 250
                """
            )
        )
        entity_payload = entity_rows.mappings().all()
    else:
        entity_payload = []

    gold_count = await _safe_count(
        db,
        "dataset_gold_records",
        select(func.count()).select_from(GoldRecord),
    )
    raw_count = int(await db.scalar(select(func.count()).select_from(Message)) or 0)
    recent_turn_rows = recent_rows.mappings().all() if hasattr(recent_rows, "mappings") else []
    return {
        "analysis_count": int(row.analysis_count or 0),
        "correction_rate": round(int(row.correction_count or 0) / max(int(row.analysis_count or 0), 1), 3),
        "casual_chat_rate": round(int(row.casual_count or 0) / max(int(row.analysis_count or 0), 1), 3),
        "low_signal_rate": round(int(row.low_signal_count or 0) / max(int(row.analysis_count or 0), 1), 3),
        "gold_records_created": gold_count,
        "raw_messages": raw_count,
        "entity_samples": entity_payload[:20],
        "recent_turns": [
            {
                "transcript": item.transcript_final,
                "intent_label": item.intent_label,
                "intent_confidence": float(item.intent_confidence or 0.0),
                "primary_language": item.primary_language,
                "applied_keyterms": list((item.keyterms_json or {}).get("applied", [])),
                "usable_for_learning": bool((item.quality_json or {}).get("usable_for_learning", False)),
            }
            for item in recent_turn_rows
        ],
    }
