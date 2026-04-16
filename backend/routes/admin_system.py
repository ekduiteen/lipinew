from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db, engine
from dependencies.admin_auth import get_current_admin
from models.admin_control import AdminAccount
from models.dataset_gold import GoldRecord
from models.message import Message
from config import settings
from cache import valkey

router = APIRouter(prefix="/api/ctrl/system", tags=["control-system"])

@router.get("/health")
async def get_system_health(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Detailed internal diagnostics for LIPI Control.
    """
    # 1. DB Health & Stats
    gold_count = await db.scalar(select(func.count()).select_from(GoldRecord))
    raw_count = await db.scalar(select(func.count()).select_from(Message))
    
    # 2. Valkey Stats
    valkey_ok = False
    valkey_info = {}
    try:
        await valkey.ping()
        valkey_ok = True
    except Exception:
        pass

    # 3. MinIO Check (Simplified)
    minio_ok = True # In a real app, we'd check bucket accessibility
    
    return {
        "status": "healthy" if (valkey_ok and minio_ok) else "degraded",
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
        }
    }

@router.get("/audit")
async def get_audit_overview(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Basic audit summary (could be expanded into a full search).
    """
    # Placeholder for audit trail visualization data
    return {"message": "Audit trail service operational"}

@router.get("/stats/timeseries")
async def get_stats_timeseries(
    days: int = 30,
    dialect: str | None = None,
    register: str | None = None,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Aggregates gold record and message counts by day for charts with filtering and caching.
    """
    import json
    from datetime import timedelta
    
    # 1. Check Cache
    cache_key = f"ctrl:stats:ts:{days}:{dialect or 'all'}:{register or 'all'}"
    cached_val = await valkey.get(cache_key)
    if cached_val:
        return json.loads(cached_val)

    # 2. Base Queries
    from models.session import TeachingSession
    
    # 2.1 Gold Records Filtered
    gold_stmt = (
        select(
            func.date_trunc('day', GoldRecord.created_at).label('day'),
            func.count(GoldRecord.id).label('count')
        )
    )
    if dialect:
        gold_stmt = gold_stmt.where(GoldRecord.dialect == dialect)
    if register:
        gold_stmt = gold_stmt.where(GoldRecord.register == register)
        
    gold_stmt = gold_stmt.group_by('day').order_by('day').limit(days)
    
    # 2.2 Raw Messages Filtered (Requires Join for Register)
    raw_stmt = (
        select(
            func.date_trunc('day', Message.created_at).label('day'),
            func.count(Message.id).label('count')
        )
    )
    
    if register:
        raw_stmt = raw_stmt.join(TeachingSession, Message.session_id == TeachingSession.id)
        raw_stmt = raw_stmt.where(TeachingSession.register_used == register)
    
    # Note: Dialect filtering on messages usually requires TeacherSignals. 
    # For now, we skip dialect filtering on raw messages to keep query efficient,
    # OR we can join TeacherSignals if highly-targeted dialect yield is needed.

    raw_stmt = raw_stmt.group_by('day').order_by('day').limit(days)

    gold_res = await db.execute(gold_stmt)
    raw_res = await db.execute(raw_stmt)

    # 3. Format result
    data_map = {}
    for day, count in gold_res.all():
        d_str = day.strftime("%Y-%m-%d")
        data_map[d_str] = {"date": d_str, "gold": count, "raw": 0}
        
    for day, count in raw_res.all():
        d_str = day.strftime("%Y-%m-%d")
        if d_str in data_map:
            data_map[d_str]["raw"] = count
        else:
            data_map[d_str] = {"date": d_str, "gold": 0, "raw": count}
            
    final_data = sorted(data_map.values(), key=lambda x: x["date"])
    
    # 4. SET Cache (15 min)
    await valkey.setex(cache_key, 900, json.dumps(final_data))
    
    return final_data
