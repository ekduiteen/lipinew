"""Unified turn intelligence: intent, entities, keyterms, code-switching, and learning quality."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import logging
import re
import uuid

import httpx
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.intelligence import MessageAnalysis, MessageEntity
from services import llm as llm_svc
from services.entity_extractor import ExtractedEntity, extract_entities
from services.hearing import HearingResult
from services.intent_classifier import IntentResult, classify_intent
from services.keyterm_service import KeytermPreparation, match_candidates_in_text
from services.transcript_repair import TranscriptRepairResult

logger = logging.getLogger("lipi.backend.turn_intelligence")

_LLM_INTELLIGENCE_SYSTEM = """You extract structured turn intelligence from a teacher utterance.
Return only valid JSON.

Schema:
{
  "intent": {"label": "...", "confidence": 0.0, "secondary_labels": []},
  "entities": [
    {
      "text": "...",
      "normalized_text": "...",
      "entity_type": "vocabulary|proper_name|phrase|honorific_or_register_term|language_name|pronunciation_target|cultural_concept|corrected_term|gloss_or_meaning|example_usage",
      "language": "ne|en|new|mai|null",
      "confidence": 0.0,
      "attributes": {}
    }
  ],
  "quality": {"usable_for_learning": true, "reason_if_not": null}
}
"""


@dataclass(frozen=True)
class CodeSwitchAnalysis:
    primary_language: str
    secondary_language: str | None
    ratio: float
    spans: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TurnQuality:
    usable_for_learning: bool
    reason_if_not: str | None
    usability_score: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TurnIntelligence:
    intent: IntentResult
    entities: list[ExtractedEntity]
    keyterms: dict
    code_switch: CodeSwitchAnalysis
    quality: TurnQuality
    transcript_repair: TranscriptRepairResult
    learning_weight: float
    analysis_mode: str = "live"
    model_source: str = "turn_intelligence_v1"

    def to_dict(self) -> dict:
        return {
            "intent": self.intent.to_dict(),
            "entities": [entity.to_dict() for entity in self.entities],
            "keyterms": self.keyterms,
            "code_switch": self.code_switch.to_dict(),
            "quality": self.quality.to_dict(),
            "transcript_repair": self.transcript_repair.to_dict(),
            "learning_weight": self.learning_weight,
            "analysis_mode": self.analysis_mode,
            "model_source": self.model_source,
        }


def from_dict(payload: dict) -> TurnIntelligence:
    intent_payload = payload.get("intent") or {}
    entities_payload = payload.get("entities") or []
    code_switch_payload = payload.get("code_switch") or {}
    quality_payload = payload.get("quality") or {}
    repair_payload = payload.get("transcript_repair") or {}

    return TurnIntelligence(
        intent=IntentResult(
            label=str(intent_payload.get("label") or "low_signal"),
            confidence=float(intent_payload.get("confidence") or 0.0),
            secondary_labels=list(intent_payload.get("secondary_labels") or []),
            evidence=list(intent_payload.get("evidence") or []),
        ),
        entities=[
            ExtractedEntity(
                text=str(entity.get("text") or ""),
                normalized_text=str(entity.get("normalized_text") or entity.get("text") or ""),
                entity_type=str(entity.get("entity_type") or "vocabulary"),
                language=entity.get("language"),
                confidence=float(entity.get("confidence") or 0.0),
                source_span=tuple(entity.get("source_span") or [None, None]),
                attributes=dict(entity.get("attributes") or {}),
            )
            for entity in entities_payload
            if str(entity.get("text") or "").strip()
        ],
        keyterms=dict(payload.get("keyterms") or {}),
        code_switch=CodeSwitchAnalysis(
            primary_language=str(code_switch_payload.get("primary_language") or "ne"),
            secondary_language=code_switch_payload.get("secondary_language"),
            ratio=float(code_switch_payload.get("ratio") or 0.0),
            spans=list(code_switch_payload.get("spans") or []),
        ),
        quality=TurnQuality(
            usable_for_learning=bool(quality_payload.get("usable_for_learning", False)),
            reason_if_not=quality_payload.get("reason_if_not"),
            usability_score=float(quality_payload.get("usability_score") or 0.0),
        ),
        transcript_repair=TranscriptRepairResult(
            original_text=str(repair_payload.get("original_text") or ""),
            repaired_text=str(repair_payload.get("repaired_text") or ""),
            applied_repairs=list(repair_payload.get("applied_repairs") or []),
            uncertain_candidates=list(repair_payload.get("uncertain_candidates") or []),
            confidence_after=float(repair_payload.get("confidence_after") or 0.0),
        ),
        learning_weight=float(payload.get("learning_weight") or 0.0),
        analysis_mode=str(payload.get("analysis_mode") or "live"),
        model_source=str(payload.get("model_source") or "turn_intelligence_v1"),
    )


def _analyze_code_switch(
    *,
    text: str,
    hearing: HearingResult,
) -> CodeSwitchAnalysis:
    devanagari = re.findall(r"[\u0900-\u097F]+", text)
    latin = re.findall(r"[A-Za-z]+", text)
    total = max(len(devanagari) + len(latin), 1)
    ratio = round(min(len(latin), len(devanagari)) / total if devanagari and latin else (len(latin) / total if devanagari else 0.0), 3)

    spans: list[dict] = []
    for match in re.finditer(r"[\u0900-\u097F]+|[A-Za-z]+", text):
        token = match.group(0)
        language = "ne" if re.search(r"[\u0900-\u097F]", token) else "en"
        spans.append({"text": token, "language": language, "span": [match.start(), match.end()]})

    primary_language = hearing.language or "ne"
    secondary_language = None
    if devanagari and latin:
        secondary_language = "en" if primary_language != "en" else "ne"
    return CodeSwitchAnalysis(
        primary_language=primary_language,
        secondary_language=secondary_language,
        ratio=ratio,
        spans=spans[:16],
    )


def _derive_quality(
    *,
    hearing: HearingResult,
    intent: IntentResult,
    entities: list[ExtractedEntity],
) -> TurnQuality:
    usable = True
    reason = None
    score = hearing.confidence

    if hearing.quality_label == "low":
        usable = False
        reason = "low_stt_confidence"
        score = min(score, 0.25)
    elif intent.label == "low_signal" and intent.confidence >= 0.6:
        usable = False
        reason = "low_signal_turn"
        score = min(score, 0.35)
    elif not entities and hearing.confidence < 0.75:
        usable = False
        reason = "no_reliable_entities"
        score = min(score, 0.4)
    elif any(entity.entity_type == "corrected_term" for entity in entities):
        score = min(0.98, score + 0.15)

    return TurnQuality(
        usable_for_learning=usable,
        reason_if_not=reason,
        usability_score=round(max(0.0, min(score, 0.99)), 3),
    )


def _learning_weight(intent: IntentResult, quality: TurnQuality, entities: list[ExtractedEntity]) -> float:
    weight = quality.usability_score
    if intent.label == "correction":
        weight += 0.25
    elif intent.label in {"teaching", "register_instruction", "pronunciation_guidance", "code_switch_explanation"}:
        weight += 0.16
    elif intent.label == "example":
        weight += 0.08
    elif intent.label == "casual_chat":
        weight -= 0.12
    if any(entity.entity_type in {"vocabulary", "phrase", "corrected_term"} and entity.confidence >= settings.learning_min_entity_confidence for entity in entities):
        weight += 0.08
    return round(max(0.0, min(weight, 0.99)), 3)


def analyze_turn(
    *,
    hearing: HearingResult,
    repaired_transcript: TranscriptRepairResult,
    keyterms: KeytermPreparation,
    memory_context: dict | None = None,
) -> TurnIntelligence:
    code_switch = _analyze_code_switch(text=repaired_transcript.repaired_text, hearing=hearing)
    intent = classify_intent(
        hearing=hearing,
        repaired_text=repaired_transcript.repaired_text,
        keyterms=keyterms,
        memory_context=memory_context,
    )
    entities = extract_entities(
        text=repaired_transcript.repaired_text,
        intent=intent,
        keyterms=keyterms,
        primary_language=code_switch.primary_language,
    )
    quality = _derive_quality(
        hearing=hearing,
        intent=intent,
        entities=entities,
    )
    keyterm_matches = match_candidates_in_text(repaired_transcript.repaired_text, keyterms)
    keyterm_payload = {
        **keyterms.to_dict(),
        **keyterm_matches,
    }
    learning_weight = _learning_weight(intent, quality, entities)
    return TurnIntelligence(
        intent=intent,
        entities=entities,
        keyterms=keyterm_payload,
        code_switch=code_switch,
        quality=quality,
        transcript_repair=repaired_transcript,
        learning_weight=learning_weight,
    )


async def enrich_with_llm(
    *,
    teacher_text: str,
    live_analysis: TurnIntelligence,
    http: httpx.AsyncClient,
) -> TurnIntelligence:
    messages = [
        {"role": "system", "content": _LLM_INTELLIGENCE_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "teacher_text": teacher_text,
                    "hint_intent": live_analysis.intent.to_dict(),
                    "hint_entities": [entity.to_dict() for entity in live_analysis.entities],
                    "quality_hint": live_analysis.quality.to_dict(),
                    "keyterms": live_analysis.keyterms,
                },
                ensure_ascii=False,
            ),
        },
    ]
    raw = await llm_svc.generate(messages, http, stream=False)
    if not isinstance(raw, str):
        return live_analysis
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        payload = json.loads(cleaned)
    except Exception:
        return live_analysis

    intent_payload = payload.get("intent") or {}
    entities_payload = payload.get("entities") or []
    quality_payload = payload.get("quality") or {}

    intent = IntentResult(
        label=str(intent_payload.get("label") or live_analysis.intent.label),
        confidence=round(float(intent_payload.get("confidence") or live_analysis.intent.confidence), 3),
        secondary_labels=list(intent_payload.get("secondary_labels") or live_analysis.intent.secondary_labels),
        evidence=list(live_analysis.intent.evidence),
    )
    entities: list[ExtractedEntity] = []
    for entity in entities_payload:
        text_value = str(entity.get("text") or "").strip()
        if not text_value:
            continue
        entities.append(
            ExtractedEntity(
                text=text_value,
                normalized_text=str(entity.get("normalized_text") or text_value.lower()),
                entity_type=str(entity.get("entity_type") or "vocabulary"),
                language=entity.get("language"),
                confidence=round(float(entity.get("confidence") or 0.55), 3),
                source_span=(None, None),
                attributes=dict(entity.get("attributes") or {}),
            )
        )
    if not entities:
        entities = live_analysis.entities

    quality = TurnQuality(
        usable_for_learning=bool(quality_payload.get("usable_for_learning", live_analysis.quality.usable_for_learning)),
        reason_if_not=quality_payload.get("reason_if_not", live_analysis.quality.reason_if_not),
        usability_score=round(float(quality_payload.get("usability_score") or live_analysis.quality.usability_score), 3),
    )

    return TurnIntelligence(
        intent=intent,
        entities=entities,
        keyterms=live_analysis.keyterms,
        code_switch=live_analysis.code_switch,
        quality=quality,
        transcript_repair=live_analysis.transcript_repair,
        learning_weight=_learning_weight(intent, quality, entities),
        analysis_mode="authoritative",
        model_source="turn_intelligence_llm_v1",
    )


async def persist_turn_intelligence(
    db: AsyncSession,
    *,
    message_id: str,
    session_id: str,
    teacher_id: str | None,
    transcript_original: str,
    transcript_final: str,
    intelligence: TurnIntelligence,
) -> None:
    try:
        async with db.begin_nested():
            analysis = (
                await db.execute(select(MessageAnalysis).where(MessageAnalysis.message_id == message_id))
            ).scalar_one_or_none()
            if analysis is None:
                analysis = MessageAnalysis(
                    id=str(uuid.uuid4()),
                    message_id=message_id,
                    session_id=session_id,
                    teacher_id=teacher_id,
                )
                db.add(analysis)

            analysis.analysis_version = "turn_intelligence_v1"
            analysis.analysis_mode = intelligence.analysis_mode
            analysis.primary_language = intelligence.code_switch.primary_language
            analysis.secondary_languages = [value for value in [intelligence.code_switch.secondary_language] if value]
            analysis.transcript_original = transcript_original
            analysis.transcript_final = transcript_final
            analysis.transcript_repair_metadata = intelligence.transcript_repair.to_dict()
            analysis.intent_label = intelligence.intent.label
            analysis.intent_confidence = intelligence.intent.confidence
            analysis.secondary_labels = intelligence.intent.secondary_labels
            analysis.keyterms_json = intelligence.keyterms
            analysis.code_switch_json = intelligence.code_switch.to_dict()
            analysis.quality_json = intelligence.quality.to_dict()
            analysis.usability_score = intelligence.quality.usability_score
            analysis.learning_weight = intelligence.learning_weight
            analysis.model_source = intelligence.model_source
            await db.flush()

            await db.execute(delete(MessageEntity).where(MessageEntity.message_id == message_id))
            for entity in intelligence.entities:
                db.add(
                    MessageEntity(
                        id=str(uuid.uuid4()),
                        message_id=message_id,
                        session_id=session_id,
                        teacher_id=teacher_id,
                        text=entity.text,
                        normalized_text=entity.normalized_text,
                        entity_type=entity.entity_type,
                        language=entity.language,
                        confidence=entity.confidence,
                        source_start=entity.source_span[0],
                        source_end=entity.source_span[1],
                        attributes_json=entity.attributes,
                    )
                )
            await db.flush()
    except SQLAlchemyError as exc:
        logger.warning("Turn intelligence persistence unavailable: %s", exc)
