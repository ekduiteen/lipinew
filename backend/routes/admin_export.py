from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_db
from dependencies.admin_auth import get_current_admin
from models.admin_control import AdminAccount
from models.dataset_gold import DatasetSnapshot
from services.admin_export import create_dataset_snapshot, open_snapshot_stream

router = APIRouter(prefix="/api/ctrl/datasets", tags=["control-datasets"])


class SnapshotFilters(BaseModel):
    language: Optional[str] = None
    dialect: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    confidence_threshold: Optional[float] = None


class SnapshotRequest(BaseModel):
    name: str
    version: str
    filters: Optional[SnapshotFilters] = None


@router.get("/")
async def list_snapshots(
    limit: int = 50,
    offset: int = 0,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DatasetSnapshot)
        .order_by(DatasetSnapshot.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    snapshots = result.scalars().all()
    return {"snapshots": snapshots, "limit": limit, "offset": offset}


@router.post("/snapshot")
async def create_snapshot(
    data: SnapshotRequest,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        snapshot = await create_dataset_snapshot(
            db=db,
            admin=admin,
            name=data.name,
            version=data.version,
            filters=data.filters.model_dump(exclude_none=True, mode="json") if data.filters else None,
        )
        return {"status": "created", "snapshot_id": snapshot.id, "url": snapshot.download_url}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}")


@router.get("/download/{snapshot_id}")
async def download_snapshot(
    snapshot_id: str,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    snapshot = await db.get(DatasetSnapshot, snapshot_id)
    if snapshot is None or not snapshot.download_url:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    try:
        minio_response = open_snapshot_stream(snapshot.download_url)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not available: {exc}")

    filename = f"{snapshot.dataset_name}-{snapshot.version}.zip"

    async def _iter_stream():
        try:
            while True:
                chunk = await __import__("asyncio").to_thread(minio_response.read, 1024 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            minio_response.close()
            minio_response.release_conn()

    return StreamingResponse(
        _iter_stream(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
