from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
import zipfile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.dataset_gold import GoldRecord, DatasetSnapshot
from models.admin_control import AdminAccount
from services.audio_storage import _build_client, _normalize_object_name, fetch_teacher_audio
from config import settings

logger = logging.getLogger("lipi.backend.admin.export")

async def create_dataset_snapshot(
    db: AsyncSession,
    admin: AdminAccount,
    name: str,
    version: str,
    filters: dict | None = None
) -> DatasetSnapshot:
    """
    Groups GoldRecords by filters and produces a ZIP artifact in MinIO.
    """
    # 1. Query records
    stmt = select(GoldRecord).where(GoldRecord.is_published == True)
    
    # Apply simple filters (e.g., by dialect)
    if filters and "dialect" in filters:
        stmt = stmt.where(GoldRecord.dialect == filters["dialect"])
        
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    snapshot = DatasetSnapshot(
        id=str(uuid.uuid4()),
        dataset_name=name,
        version=version,
        record_count=len(records),
        filter_query=filters or {},
        created_by=admin.id
    )
    db.add(snapshot)
    await db.flush()

    # 2. Generate ZIP in memory (Simplified for MVP)
    # In a real enterprise app, this would be a background task (Celery/Temporal)
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        metadata = []
        for i, rec in enumerate(records):
            # Add audio if it exists
            if rec.audio_path:
                audio_data = await fetch_teacher_audio(rec.audio_path)
                if audio_data:
                    audio_filename = f"audio/{rec.id}.wav"
                    zip_file.writestr(audio_filename, audio_data)
                    
            metadata.append({
                "id": rec.id,
                "transcript": rec.corrected_transcript,
                "raw_stt": rec.raw_transcript,
                "dialect": rec.dialect,
                "register": rec.register,
                "tags": rec.tags,
                "audio_file": f"audio/{rec.id}.wav" if rec.audio_path else None
            })
            
        zip_file.writestr("metadata.jsonl", "\n".join(json.dumps(m) for m in metadata))

    # 3. Upload to MinIO
    client = _build_client()
    object_name = f"datasets/{snapshot.id}/{name}-{version}.zip"
    zip_bytes = zip_buffer.getvalue()
    
    await asyncio.to_thread(
        client.put_object,
        settings.minio_bucket_audio, # Reusing for now or could use a new bucket
        object_name,
        BytesIO(zip_bytes),
        length=len(zip_bytes),
        content_type="application/zip"
    )
    
    snapshot.download_url = object_name
    await db.commit()
    await db.refresh(snapshot)
    
    return snapshot
