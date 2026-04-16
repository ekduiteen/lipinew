from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.connection import get_db
from dependencies.admin_auth import get_current_admin
from models.admin_control import AdminAccount
from models.dataset_gold import DatasetSnapshot
from services.admin_export import create_dataset_snapshot

router = APIRouter(prefix="/api/ctrl/datasets", tags=["control-datasets"])

class SnapshotRequest(BaseModel):
    name: str
    version: str
    filters: Optional[dict] = None

@router.get("/")
async def list_snapshots(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all available dataset releases."""
    result = await db.execute(select(DatasetSnapshot).order_by(DatasetSnapshot.created_at.desc()))
    snapshots = result.scalars().all()
    return {"snapshots": snapshots}

@router.post("/snapshot")
async def create_snapshot(
    data: SnapshotRequest,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Trigger a new dataset version release."""
    try:
        snapshot = await create_dataset_snapshot(
            db=db,
            admin=admin,
            name=data.name,
            version=data.version,
            filters=data.filters
        )
        return {"status": "created", "snapshot_id": snapshot.id, "url": snapshot.download_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
