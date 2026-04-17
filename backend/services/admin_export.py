from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from io import BytesIO
import zipfile

from minio.error import S3Error
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.admin_control import AdminAccount, AdminAuditLog
from models.dataset_gold import DatasetSnapshot, GoldRecord
from services.audio_storage import _build_client, fetch_teacher_audio

logger = logging.getLogger("lipi.backend.admin.export")


def build_gold_export_query(filters: dict | None = None) -> Select:
    stmt = select(GoldRecord).where(GoldRecord.is_published.is_(True))
    filters = filters or {}
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if isinstance(date_from, str):
        date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
    if isinstance(date_to, str):
        date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
    if filters.get("language"):
        stmt = stmt.where(GoldRecord.primary_language == filters["language"])
    if filters.get("dialect"):
        stmt = stmt.where(GoldRecord.dialect == filters["dialect"])
    if date_from:
        stmt = stmt.where(GoldRecord.created_at >= date_from)
    if date_to:
        stmt = stmt.where(GoldRecord.created_at <= date_to)
    if filters.get("confidence_threshold") is not None:
        stmt = stmt.where(GoldRecord.audio_quality_score >= float(filters["confidence_threshold"]))
    return stmt.order_by(GoldRecord.created_at.desc())


async def create_dataset_snapshot(
    db: AsyncSession,
    admin: AdminAccount,
    name: str,
    version: str,
    filters: dict | None = None,
) -> DatasetSnapshot:
    stmt = build_gold_export_query(filters)
    result = await db.execute(stmt)
    records = result.scalars().all()

    snapshot = DatasetSnapshot(
        id=str(uuid.uuid4()),
        dataset_name=name,
        version=version,
        record_count=len(records),
        filter_query=filters or {},
        created_by=admin.id,
    )
    db.add(snapshot)
    await db.flush()

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        metadata = []
        for rec in records:
            audio_filename = None
            if rec.audio_path:
                audio_data = await fetch_teacher_audio(rec.audio_path)
                if audio_data:
                    audio_filename = f"audio/{rec.id}.wav"
                    zip_file.writestr(audio_filename, audio_data)

            metadata.append(
                {
                    "id": rec.id,
                    "transcript": rec.corrected_transcript,
                    "raw_stt": rec.raw_transcript,
                    "language": rec.primary_language,
                    "dialect": rec.dialect,
                    "register": rec.register,
                    "tags": rec.tags,
                    "audio_quality_score": rec.audio_quality_score,
                    "audio_file": audio_filename,
                }
            )

        zip_file.writestr("metadata.jsonl", "\n".join(json.dumps(row) for row in metadata))

    object_name = f"datasets/{snapshot.id}/{name}-{version}.zip"
    zip_bytes = zip_buffer.getvalue()
    client = _build_client()
    await asyncio.to_thread(
        client.put_object,
        settings.minio_bucket_audio,
        object_name,
        BytesIO(zip_bytes),
        length=len(zip_bytes),
        content_type="application/zip",
    )

    snapshot.download_url = object_name
    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="create_dataset_snapshot",
            entity_type="DatasetSnapshot",
            entity_id=snapshot.id,
            details={
                "dataset_name": name,
                "version": version,
                "filters": filters or {},
                "record_count": len(records),
            },
        )
    )
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


def open_snapshot_stream(object_name: str):
    client = _build_client()
    return client.get_object(settings.minio_bucket_audio, object_name)
