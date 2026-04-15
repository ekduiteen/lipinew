"""Dashboard API - system health, data quality, and collection reports."""

from __future__ import annotations

import json
from collections import Counter

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cache import valkey
from config import settings
from db.connection import get_db
from dependencies.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class ServiceStatus(BaseModel):
    ok: bool
    detail: dict | None = None


class QueueStatus(BaseModel):
    pending: int
    processing: int
    dead_letter: int


class DataSummary(BaseModel):
    total_sessions: int
    total_messages: int
    total_teacher_turns: int
    total_lipi_turns: int
    total_vocabulary_entries: int
    avg_stt_confidence: float | None


class QualityReport(BaseModel):
    recent_teacher_language_counts: dict[str, int]
    recent_low_confidence_turns: int
    recent_learning_eligible_turns: int
    recent_confused_replies: int
    recent_hindi_mixed_replies: int


class RecentSample(BaseModel):
    teacher_text: str
    teacher_language: str | None
    stt_confidence: float | None
    lipi_text: str


class DashboardOverview(BaseModel):
    system: dict[str, ServiceStatus]
    queues: QueueStatus
    data: DataSummary
    quality: QualityReport
    recent_samples: list[RecentSample]


_CONFUSED_REPLY_MARKERS = (
    "मलाई थाहा भएन",
    "के तिमीले फेरि भन्न सक्छौ",
    "कृपया फेरि भन्नुहोस्",
    "मैले गलत बुझें",
    "के मैले सही बुझें",
    "मलाई लाग्छ",
)
_HINDI_REPLY_MARKERS = ("कैसे", "क्या", "है", "हूँ", "हैं", "नहीं", "लेकिन")


async def _fetch_json(http, url: str) -> tuple[bool, dict | None]:
    try:
        resp = await http.get(url, timeout=4.0)
        resp.raise_for_status()
        return True, resp.json()
    except Exception:
        return False, None


def _is_confused_reply(text_value: str) -> bool:
    return any(marker in text_value for marker in _CONFUSED_REPLY_MARKERS)


def _is_hindi_mixed_reply(text_value: str) -> bool:
    lowered = text_value.lower()
    return any(marker in lowered for marker in _HINDI_REPLY_MARKERS)


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardOverview:
    del user_id

    http = request.app.state.http
    db_ok = True
    valkey_ok = False
    try:
        valkey_ok = bool(await valkey.ping())
    except Exception:
        valkey_ok = False

    vllm_ok, vllm_detail = await _fetch_json(http, f"{settings.vllm_url}/v1/models")
    ml_ok, ml_detail = await _fetch_json(http, f"{settings.ml_service_url}/models/info")

    pending, processing, dead_letter = await valkey.llen(settings.learning_queue_key), await valkey.llen(
        settings.learning_processing_key
    ), await valkey.llen(settings.learning_dead_letter_key)

    totals = await db.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM teaching_sessions) AS total_sessions,
                (SELECT COUNT(*) FROM messages) AS total_messages,
                (SELECT COUNT(*) FROM messages WHERE role = 'teacher') AS total_teacher_turns,
                (SELECT COUNT(*) FROM messages WHERE role = 'lipi') AS total_lipi_turns,
                (SELECT COUNT(*) FROM vocabulary_entries) AS total_vocabulary_entries,
                (SELECT AVG(stt_confidence) FROM messages WHERE role = 'teacher' AND stt_confidence IS NOT NULL) AS avg_stt_confidence
            """
        )
    )
    total_row = totals.one()

    recent_rows = await db.execute(
        text(
            """
            SELECT
                teacher.detected_language AS teacher_language,
                teacher.stt_confidence AS stt_confidence,
                teacher.text AS teacher_text,
                lipi.text AS lipi_text
            FROM messages teacher
            JOIN messages lipi
              ON lipi.session_id = teacher.session_id
             AND lipi.turn_index = teacher.turn_index + 1
            WHERE teacher.role = 'teacher'
              AND lipi.role = 'lipi'
            ORDER BY teacher.created_at DESC
            LIMIT 40
            """
        )
    )
    recent_pairs = recent_rows.mappings().all()

    language_counts = Counter((row["teacher_language"] or "unknown") for row in recent_pairs)
    low_conf_turns = 0
    learning_eligible_turns = 0
    confused_replies = 0
    hindi_mixed_replies = 0
    samples: list[RecentSample] = []

    for row in recent_pairs:
        teacher_language = row["teacher_language"]
        stt_confidence = float(row["stt_confidence"] or 0.0)
        teacher_text = str(row["teacher_text"] or "")
        lipi_text = str(row["lipi_text"] or "")

        if stt_confidence < settings.learning_min_stt_confidence:
            low_conf_turns += 1
        if _is_confused_reply(lipi_text):
            confused_replies += 1
        if _is_hindi_mixed_reply(lipi_text):
            hindi_mixed_replies += 1

        is_eligible = (
            (teacher_language or "").lower() == settings.learning_required_teacher_language
            and stt_confidence >= settings.learning_min_stt_confidence
            and 0 < len(lipi_text) <= settings.learning_max_reply_chars
            and not _is_confused_reply(lipi_text)
            and not _is_hindi_mixed_reply(lipi_text)
        )
        if is_eligible:
            learning_eligible_turns += 1

        if len(samples) < 8:
            samples.append(
                RecentSample(
                    teacher_text=teacher_text[:200],
                    teacher_language=teacher_language,
                    stt_confidence=row["stt_confidence"],
                    lipi_text=lipi_text[:240],
                )
            )

    return DashboardOverview(
        system={
            "database": ServiceStatus(ok=db_ok, detail=None),
            "valkey": ServiceStatus(ok=valkey_ok, detail=None),
            "vllm": ServiceStatus(ok=vllm_ok, detail=vllm_detail),
            "ml": ServiceStatus(ok=ml_ok, detail=ml_detail),
        },
        queues=QueueStatus(
            pending=pending,
            processing=processing,
            dead_letter=dead_letter,
        ),
        data=DataSummary(
            total_sessions=int(total_row.total_sessions or 0),
            total_messages=int(total_row.total_messages or 0),
            total_teacher_turns=int(total_row.total_teacher_turns or 0),
            total_lipi_turns=int(total_row.total_lipi_turns or 0),
            total_vocabulary_entries=int(total_row.total_vocabulary_entries or 0),
            avg_stt_confidence=(float(total_row.avg_stt_confidence) if total_row.avg_stt_confidence is not None else None),
        ),
        quality=QualityReport(
            recent_teacher_language_counts=dict(language_counts),
            recent_low_confidence_turns=low_conf_turns,
            recent_learning_eligible_turns=learning_eligible_turns,
            recent_confused_replies=confused_replies,
            recent_hindi_mixed_replies=hindi_mixed_replies,
        ),
        recent_samples=samples,
    )
