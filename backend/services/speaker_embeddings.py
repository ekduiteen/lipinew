"""Async speaker embedding extraction and storage."""

from __future__ import annotations

import logging
import uuid

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from services import audio_storage as audio_storage_svc
from services import speaker_clustering as speaker_clustering_svc

logger = logging.getLogger("lipi.backend.speaker_embeddings")

_MIN_EMBED_CONFIDENCE = 0.75
_MIN_AUDIO_MS = 1200
_EXPECTED_DIMENSIONS = 512


class SpeakerEmbeddingError(RuntimeError):
    pass


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


def _is_quality_eligible(
    *,
    audio_path: str | None,
    stt_confidence: float,
    hearing_result: dict | None,
) -> tuple[bool, str]:
    if not audio_path:
        return False, "missing_audio_path"
    if stt_confidence < _MIN_EMBED_CONFIDENCE:
        return False, f"low_stt_confidence={stt_confidence:.2f}"
    if hearing_result and not bool(hearing_result.get("learning_allowed", True)):
        return False, "hearing_blocked"
    duration_ms = int((hearing_result or {}).get("audio_duration_ms") or 0)
    if 0 < duration_ms < _MIN_AUDIO_MS:
        return False, f"audio_too_short={duration_ms}"
    return True, "ok"


async def extract_embedding(
    *,
    http: httpx.AsyncClient,
    audio_bytes: bytes,
) -> dict:
    files = {"audio": ("speaker.wav", audio_bytes, "audio/wav")}
    response = await http.post(
        f"{settings.ml_service_url}/speaker-embed",
        files=files,
        timeout=settings.ml_timeout,
    )
    response.raise_for_status()
    payload = response.json()
    embedding = payload.get("embedding")
    dimensions = int(payload.get("dimensions", 0) or 0)

    if not isinstance(embedding, list):
        raise SpeakerEmbeddingError("embedding payload missing list")
    if dimensions != _EXPECTED_DIMENSIONS or len(embedding) != _EXPECTED_DIMENSIONS:
        raise SpeakerEmbeddingError(
            f"invalid embedding dimensions={dimensions} len={len(embedding)}"
        )

    try:
        normalized = [float(value) for value in embedding]
    except (TypeError, ValueError) as exc:
        raise SpeakerEmbeddingError("embedding contains non-float values") from exc

    for value in normalized:
        if value != value or value in (float("inf"), float("-inf")):
            raise SpeakerEmbeddingError("embedding contains invalid numeric values")

    payload["embedding"] = normalized
    return payload


async def extract_and_store(
    *,
    db: AsyncSession,
    http: httpx.AsyncClient,
    teacher_id: str,
    session_id: str,
    audio_path: str | None,
    detected_language: str | None,
    stt_confidence: float,
    hearing_result: dict | None,
) -> tuple[bool, str]:
    eligible, reason = _is_quality_eligible(
        audio_path=audio_path,
        stt_confidence=stt_confidence,
        hearing_result=hearing_result,
    )
    if not eligible:
        return False, reason

    audio_bytes = await audio_storage_svc.fetch_teacher_audio(audio_path)
    if not audio_bytes:
        return False, "audio_fetch_failed"

    payload = await extract_embedding(http=http, audio_bytes=audio_bytes)
    vector = _vector_literal(payload["embedding"])
    duration_ms = int(payload.get("duration_ms", 0) or 0)
    if duration_ms < _MIN_AUDIO_MS:
        return False, f"embedded_audio_too_short={duration_ms}"

    embedding_id = str(uuid.uuid4())
    await db.execute(
        text(
            """
            INSERT INTO speaker_embeddings
                (id, teacher_id, session_id, embedding, audio_path, audio_duration_ms, detected_language)
            VALUES
                (:id, :teacher_id, :session_id, CAST(:embedding AS vector), :audio_path, :audio_duration_ms, :detected_language)
            """
        ),
        {
            "id": embedding_id,
            "teacher_id": teacher_id,
            "session_id": session_id,
            "embedding": vector,
            "audio_path": audio_path,
            "audio_duration_ms": duration_ms,
            "detected_language": (detected_language or "")[:10] or None,
        },
    )
    cluster_id = await speaker_clustering_svc.assign_cluster(
        db,
        embedding_id=embedding_id,
        detected_language=detected_language,
    )
    logger.info(
        "Stored speaker embedding teacher=%s session=%s language=%s duration_ms=%s cluster=%s",
        teacher_id,
        session_id,
        detected_language,
        duration_ms,
        cluster_id,
    )
    return True, "stored"
