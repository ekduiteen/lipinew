"""Best-effort raw audio capture storage for teacher turns."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from io import BytesIO
import uuid

from minio import Minio

from config import settings


def _build_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _put_object(object_name: str, payload: bytes) -> None:
    client = _build_client()
    client.put_object(
        settings.minio_bucket_audio,
        object_name,
        BytesIO(payload),
        length=len(payload),
        content_type="application/octet-stream",
    )


async def store_teacher_audio(
    *,
    audio_bytes: bytes,
    session_id: str,
    teacher_id: str,
    turn_index: int,
) -> str | None:
    if not audio_bytes:
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    object_name = (
        f"raw-teacher-audio/{teacher_id}/{session_id}/"
        f"{turn_index:04d}-{timestamp}-{uuid.uuid4().hex}.bin"
    )
    try:
        await asyncio.to_thread(_put_object, object_name, audio_bytes)
        return object_name
    except Exception:
        return f"capture_pending://{object_name}"


async def store_phrase_audio(
    *,
    audio_bytes: bytes,
    user_id: str,
    phrase_id: str,
    suffix: str | None = None,
) -> str | None:
    if not audio_bytes:
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    extra = f"-{suffix}" if suffix else ""
    object_name = (
        f"phrase-lab-audio/{user_id}/{phrase_id}/"
        f"{timestamp}-{uuid.uuid4().hex}{extra}.bin"
    )
    try:
        await asyncio.to_thread(_put_object, object_name, audio_bytes)
        return object_name
    except Exception:
        return f"capture_pending://{object_name}"


def _normalize_object_name(audio_path: str) -> str:
    if audio_path.startswith("capture_pending://"):
        return audio_path.removeprefix("capture_pending://")
    return audio_path


def _get_object_bytes(object_name: str) -> bytes:
    client = _build_client()
    response = client.get_object(settings.minio_bucket_audio, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


async def fetch_teacher_audio(audio_path: str | None) -> bytes | None:
    if not audio_path:
        return None
    object_name = _normalize_object_name(audio_path)
    try:
        return await asyncio.to_thread(_get_object_bytes, object_name)
    except Exception:
        return None
