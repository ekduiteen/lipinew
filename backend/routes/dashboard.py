"""Dashboard API - system health, data quality, and collection reports."""

from __future__ import annotations

import inspect
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
from services import speaker_clustering as speaker_clustering_svc

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
    recent_medium_confidence_turns: int
    recent_learning_eligible_turns: int
    recent_conversation_only_turns: int
    recent_confused_replies: int
    recent_hindi_mixed_replies: int
    hearing_confidence_distribution: dict[str, int]
    correction_event_count: int
    memory_snapshot_count: int
    credibility_event_count: int
    teacher_signal_count: int
    speaker_embedding_count: int
    speaker_cluster_count: int


class RecentSample(BaseModel):
    teacher_text: str
    teacher_language: str | None
    stt_confidence: float | None
    lipi_text: str


class TurnIntelligenceSample(BaseModel):
    transcript: str
    intent_label: str
    intent_confidence: float
    primary_language: str | None
    usable_for_learning: bool
    applied_keyterms: list[str]
    entities: list[dict]


class TurnIntelligenceReport(BaseModel):
    intent_distribution: dict[str, int]
    top_entities_by_language: dict[str, list[dict]]
    correction_rate: float
    casual_chat_rate: float
    low_signal_rate: float
    keyterm_hit_quality: dict[str, float]
    top_uncertain_words: list[dict]
    per_language_extraction_quality: dict[str, float]
    recent_turns: list[TurnIntelligenceSample]


class DashboardOverview(BaseModel):
    system: dict[str, ServiceStatus]
    queues: QueueStatus
    data: DataSummary
    quality: QualityReport
    curriculum: dict
    speaker_embeddings: dict
    recent_samples: list[RecentSample]
    turn_intelligence: TurnIntelligenceReport


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
        maybe_raise = resp.raise_for_status()
        if inspect.isawaitable(maybe_raise):
            await maybe_raise
        payload = resp.json()
        if inspect.isawaitable(payload):
            payload = await payload
        return True, payload if isinstance(payload, dict) else None
    except Exception:
        return False, None


def _is_confused_reply(text_value: str) -> bool:
    return any(marker in text_value for marker in _CONFUSED_REPLY_MARKERS)


def _is_hindi_mixed_reply(text_value: str) -> bool:
    lowered = text_value.lower()
    return any(marker in lowered for marker in _HINDI_REPLY_MARKERS)


def _json_or_default(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return value


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
                (SELECT AVG(stt_confidence) FROM messages WHERE role = 'teacher' AND stt_confidence IS NOT NULL) AS avg_stt_confidence,
                (SELECT COUNT(*) FROM correction_events) AS correction_event_count,
                (SELECT COUNT(*) FROM session_memory_snapshots) AS memory_snapshot_count,
                (SELECT COUNT(*) FROM teacher_credibility_events) AS credibility_event_count,
                (SELECT COUNT(*) FROM teacher_signals) AS teacher_signal_count
            """
        )
    )
    total_row = totals.one()
    try:
        speaker_embedding_count = int(
            await db.scalar(text("SELECT COUNT(*) FROM speaker_embeddings")) or 0
        )
        speaker_cluster_count = int(
            await db.scalar(text("SELECT COUNT(DISTINCT dialect_cluster_id) FROM speaker_embeddings WHERE dialect_cluster_id IS NOT NULL")) or 0
        )
    except Exception:
        speaker_embedding_count = 0
        speaker_cluster_count = 0

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

    topic_distribution_rows = await db.execute(
        text(
            """
            SELECT topic_key, COUNT(*) AS count
            FROM curriculum_prompt_events
            GROUP BY topic_key
            ORDER BY count DESC
            """
        )
    )
    global_coverage_rows = await db.execute(
        text(
            """
            SELECT topic_key, register_key, language_key, coverage_score, unique_user_count, correction_density
            FROM global_language_coverage
            ORDER BY coverage_score ASC, unique_user_count ASC
            """
        )
    )
    repetition_rows = await db.execute(
        text(
            """
            SELECT user_id, question_type, COUNT(*) AS repeat_count
            FROM curriculum_prompt_events
            GROUP BY user_id, question_type
            HAVING COUNT(*) > 1
            ORDER BY repeat_count DESC
            LIMIT 10
            """
        )
    )
    lane_rows = await db.execute(
        text(
            """
            SELECT assigned_lane, COUNT(*) AS user_count
            FROM user_curriculum_profiles
            GROUP BY assigned_lane
            ORDER BY user_count DESC
            """
        )
    )
    correction_yield_rows = await db.execute(
        text(
            """
            SELECT topic_key, correction_density
            FROM global_language_coverage
            ORDER BY correction_density DESC
            LIMIT 12
            """
        )
    )

    language_counts = Counter((row["teacher_language"] or "unknown") for row in recent_pairs)
    low_conf_turns = 0
    medium_conf_turns = 0
    learning_eligible_turns = 0
    conversation_only_turns = 0
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
        elif stt_confidence < 0.74:
            medium_conf_turns += 1
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
        else:
            conversation_only_turns += 1

        if len(samples) < 8:
            samples.append(
                RecentSample(
                    teacher_text=teacher_text[:200],
                    teacher_language=teacher_language,
                    stt_confidence=row["stt_confidence"],
                    lipi_text=lipi_text[:240],
                )
            )

    topic_distribution = {
        str(row.topic_key): int(row.count or 0)
        for row in topic_distribution_rows
    }
    global_coverage = [
        {
            "topic_key": row.topic_key,
            "register_key": row.register_key,
            "language_key": row.language_key,
            "coverage_score": float(row.coverage_score or 0.0),
            "unique_user_count": int(row.unique_user_count or 0),
            "correction_density": float(row.correction_density or 0.0),
        }
        for row in global_coverage_rows
    ]
    under_collected_topics = global_coverage[:8]
    over_collected_topics = list(reversed(global_coverage[-8:])) if global_coverage else []
    question_type_repetition = [
        {
            "user_id": str(row.user_id),
            "question_type": row.question_type,
            "repeat_count": int(row.repeat_count or 0),
        }
        for row in repetition_rows
    ]
    unique_users_per_lane = {
        str(row.assigned_lane): int(row.user_count or 0)
        for row in lane_rows
    }
    correction_yield_by_topic = {
        str(row.topic_key): float(row.correction_density or 0.0)
        for row in correction_yield_rows
    }
    try:
        speaker_cluster_summary = await speaker_clustering_svc.get_cluster_summary(db)
    except Exception:
        speaker_cluster_summary = {
            "total_embeddings": 0,
            "assigned_clusters": 0,
            "cluster_count": 0,
            "clusters": [],
        }
    analysis_rows = await db.execute(
        text(
            """
            SELECT
                ma.message_id,
                ma.intent_label,
                ma.intent_confidence,
                ma.primary_language,
                ma.keyterms_json,
                ma.quality_json,
                ma.code_switch_json,
                ma.transcript_repair_metadata,
                ma.transcript_final,
                me.text AS entity_text,
                me.normalized_text,
                me.entity_type,
                me.language AS entity_language,
                me.confidence AS entity_confidence
            FROM message_analysis ma
            LEFT JOIN message_entities me
              ON me.message_id = ma.message_id
            ORDER BY ma.created_at DESC
            LIMIT 300
            """
        )
    )
    analysis_data = analysis_rows.mappings().all()
    intent_distribution: Counter[str] = Counter()
    entity_counts: dict[str, Counter[str]] = {}
    extraction_quality: dict[str, list[float]] = {}
    recent_turns_map: dict[str, dict] = {}
    total_analysis_rows = 0
    correction_count = 0
    casual_count = 0
    low_signal_count = 0
    keyterm_hits = 0
    keyterm_turns = 0
    repair_turns = 0

    for row in analysis_data:
        message_id = str(row["message_id"])
        if message_id not in recent_turns_map:
            total_analysis_rows += 1
            intent_label = str(row["intent_label"] or "unknown")
            intent_distribution[intent_label] += 1
            if intent_label == "correction":
                correction_count += 1
            if intent_label == "casual_chat":
                casual_count += 1
            if intent_label == "low_signal":
                low_signal_count += 1
            keyterms_json = _json_or_default(row["keyterms_json"], {})
            quality_json = _json_or_default(row["quality_json"], {})
            applied = list(keyterms_json.get("applied", []) or [])
            if applied:
                keyterm_turns += 1
                keyterm_hits += len(applied)
            repair_meta = row["transcript_repair_metadata"] or {}
            if _json_or_default(repair_meta, {}).get("applied_repairs"):
                repair_turns += 1
            recent_turns_map[message_id] = {
                "transcript": str(row["transcript_final"] or ""),
                "intent_label": intent_label,
                "intent_confidence": float(row["intent_confidence"] or 0.0),
                "primary_language": row["primary_language"],
                "usable_for_learning": bool((quality_json or {}).get("usable_for_learning", False)),
                "applied_keyterms": applied,
                "entities": [],
            }

        if row["entity_text"]:
            language_key = str(row["entity_language"] or row["primary_language"] or "unknown")
            entity_counts.setdefault(language_key, Counter())[str(row["normalized_text"] or row["entity_text"])] += 1
            extraction_quality.setdefault(language_key, []).append(float(row["entity_confidence"] or 0.0))
            if len(recent_turns_map[message_id]["entities"]) < 6:
                recent_turns_map[message_id]["entities"].append(
                    {
                        "text": row["entity_text"],
                        "normalized_text": row["normalized_text"],
                        "entity_type": row["entity_type"],
                        "language": row["entity_language"],
                        "confidence": float(row["entity_confidence"] or 0.0),
                    }
                )

    uncertain_rows = await db.execute(
        text(
            """
            SELECT extracted_claim, COUNT(*) AS hit_count
            FROM review_queue_items
            WHERE model_source = 'learning_validation_guard'
            GROUP BY extracted_claim
            ORDER BY hit_count DESC, MAX(created_at) DESC
            LIMIT 10
            """
        )
    )
    top_uncertain_words = [
        {"text": str(claim), "count": int(count or 0)}
        for claim, count in uncertain_rows.all()
        if claim
    ]
    top_entities_by_language = {
        language: [
            {"text": entity_text, "count": count}
            for entity_text, count in counter.most_common(6)
        ]
        for language, counter in entity_counts.items()
    }
    per_language_extraction_quality = {
        language: round(sum(values) / len(values), 3)
        for language, values in extraction_quality.items()
        if values
    }
    recent_turns = [
        TurnIntelligenceSample(**row)
        for row in list(recent_turns_map.values())[:10]
    ]

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
            recent_medium_confidence_turns=medium_conf_turns,
            recent_learning_eligible_turns=learning_eligible_turns,
            recent_conversation_only_turns=conversation_only_turns,
            recent_confused_replies=confused_replies,
            recent_hindi_mixed_replies=hindi_mixed_replies,
            hearing_confidence_distribution={
                "low": low_conf_turns,
                "medium": medium_conf_turns,
                "good": max(len(recent_pairs) - low_conf_turns - medium_conf_turns, 0),
            },
            correction_event_count=int(total_row.correction_event_count or 0),
            memory_snapshot_count=int(total_row.memory_snapshot_count or 0),
            credibility_event_count=int(total_row.credibility_event_count or 0),
            teacher_signal_count=int(total_row.teacher_signal_count or 0),
            speaker_embedding_count=speaker_embedding_count,
            speaker_cluster_count=speaker_cluster_count,
        ),
        curriculum={
            "topic_distribution_by_user": topic_distribution,
            "global_topic_coverage": global_coverage,
            "under_collected_topics": under_collected_topics,
            "over_collected_topics": over_collected_topics,
            "question_type_repetition": question_type_repetition,
            "correction_yield_by_topic": correction_yield_by_topic,
            "unique_users_per_lane": unique_users_per_lane,
        },
        speaker_embeddings={
            **speaker_cluster_summary,
        },
        recent_samples=samples,
        turn_intelligence=TurnIntelligenceReport(
            intent_distribution=dict(intent_distribution),
            top_entities_by_language=top_entities_by_language,
            correction_rate=round(correction_count / max(total_analysis_rows, 1), 3),
            casual_chat_rate=round(casual_count / max(total_analysis_rows, 1), 3),
            low_signal_rate=round(low_signal_count / max(total_analysis_rows, 1), 3),
            keyterm_hit_quality={
                "avg_hits_per_keyterm_turn": round(keyterm_hits / max(keyterm_turns, 1), 3),
                "turns_with_keyterms": float(keyterm_turns),
                "turns_with_analysis": float(total_analysis_rows),
                "repair_turn_rate": round(repair_turns / max(total_analysis_rows, 1), 3),
            },
            top_uncertain_words=top_uncertain_words,
            per_language_extraction_quality=per_language_extraction_quality,
            recent_turns=recent_turns,
        ),
    )
