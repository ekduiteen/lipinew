from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from models.intelligence import (
    AdminKeytermSeed,
    MessageAnalysis,
    MessageEntity,
    ReviewQueueItem,
)
from models.message import Message
from models.session import TeachingSession
from models.user import User
from services import keyterm_service as keyterm_service_svc
from services import transcript_repair as transcript_repair_svc
from services import turn_intelligence as turn_intelligence_svc
from services.hearing import HearingResult


def _hearing(
    text: str,
    *,
    language: str = "ne",
    confidence: float = 0.91,
    mode: str = "mixed",
    quality: str = "good",
) -> HearingResult:
    return HearingResult(
        raw_text=text,
        clean_text=text,
        confidence=confidence,
        language=language,
        mode=mode,
        quality_label=quality,
        audio_quality_score=confidence,
        audio_duration_ms=1800,
        conversation_allowed=quality != "low",
        learning_allowed=quality == "good",
        reason_codes=[],
    )


@pytest.mark.asyncio
async def test_keyterm_preparation_uses_session_history_and_admin_seeds(db_session):
    teacher = User(
        id="d0000000-0000-0000-0000-000000000001",
        email="teacher@example.com",
        first_name="Mina",
        last_name="Shrestha",
        age=33,
        gender="female",
        primary_language="Nepali",
        other_languages=["English"],
        hometown="Kathmandu",
    )
    db_session.add(teacher)
    db_session.add(
        AdminKeytermSeed(
            id=str(uuid.uuid4()),
            language_key="ne",
            seed_text="तपाईं",
            normalized_text="तपाईं",
            entity_type="honorific_or_register_term",
            weight=1.0,
        )
    )
    db_session.add(
        ReviewQueueItem(
            id=str(uuid.uuid4()),
            teacher_id=teacher.id,
            session_id=None,
            extracted_claim="jojolopa",
            extraction_metadata={"review_kind": "low_trust_extraction"},
            confidence=0.32,
            model_source="learning_validation_guard",
            status="pending_review",
        )
    )
    await db_session.commit()

    prep = await keyterm_service_svc.prepare_turn_keyterms(
        db_session,
        teacher_id=teacher.id,
        session_memory={
            "active_language": "ne",
            "taught_words": ["नमस्ते", "भात"],
            "last_correction": "होइन, जोजोलोपा भन्नुहोस्",
        },
        target_language="ne",
    )

    applied = {candidate.normalized_text for candidate in prep.candidates}
    assert "नमस्ते" in applied
    assert "भात" in applied
    assert "तपाईं" in applied
    assert "jojolopa" in prep.uncertain_candidates


def test_transcript_repair_uses_keyterm_candidates():
    prep = keyterm_service_svc.KeytermPreparation(
        candidates=[
            keyterm_service_svc.KeytermCandidate(
                text="तपाईं",
                normalized_text="तपाईं",
                language="ne",
                source="admin_seed",
                weight=0.95,
                entity_type="honorific_or_register_term",
            )
        ],
        matched_from_admin_seed=["तपाईं"],
    )
    repaired = transcript_repair_svc.repair_transcript(
        transcript="तपाई भनिन्छ",
        stt_confidence=0.63,
        keyterms=prep,
    )
    assert repaired.repaired_text.startswith("तपाईं")
    assert repaired.applied_repairs


def test_turn_intelligence_detects_correction_and_entities():
    prep = keyterm_service_svc.KeytermPreparation(
        candidates=[
            keyterm_service_svc.KeytermCandidate(
                text="भात",
                normalized_text="भात",
                language="ne",
                source="session_memory",
                weight=0.95,
            )
        ],
        matched_from_session=["भात"],
    )
    repair = transcript_repair_svc.TranscriptRepairResult(
        original_text="होइन, rice होइन, भात भनिन्छ",
        repaired_text="होइन, rice होइन, भात भनिन्छ",
        confidence_after=0.9,
    )
    analysis = turn_intelligence_svc.analyze_turn(
        hearing=_hearing("होइन, rice होइन, भात भनिन्छ", language="ne", mode="mixed"),
        repaired_transcript=repair,
        keyterms=prep,
        memory_context={"last_correction": "होइन"},
    )

    assert analysis.intent.label == "correction"
    assert any(entity.entity_type == "corrected_term" for entity in analysis.entities)
    assert any(entity.entity_type in {"vocabulary", "phrase"} for entity in analysis.entities)
    assert analysis.quality.usable_for_learning is True


def test_turn_intelligence_detects_register_instruction():
    prep = keyterm_service_svc.KeytermPreparation(
        candidates=[
            keyterm_service_svc.KeytermCandidate(
                text="तिमी",
                normalized_text="तिमी",
                language="ne",
                source="admin_seed",
                weight=0.9,
                entity_type="honorific_or_register_term",
            )
        ],
        matched_from_admin_seed=["तिमी"],
    )
    repair = transcript_repair_svc.TranscriptRepairResult(
        original_text="तिमी भनेर बोल",
        repaired_text="तिमी भनेर बोल",
        confidence_after=0.94,
    )
    analysis = turn_intelligence_svc.analyze_turn(
        hearing=_hearing("तिमी भनेर बोल", language="ne", mode="nepali"),
        repaired_transcript=repair,
        keyterms=prep,
        memory_context={},
    )

    assert analysis.intent.label == "register_instruction"
    assert any(entity.entity_type == "honorific_or_register_term" for entity in analysis.entities)


@pytest.mark.asyncio
async def test_persist_turn_intelligence_creates_analysis_and_entities(db_session):
    teacher = User(
        id="d0000000-0000-0000-0000-000000000001",
        email="teacher@example.com",
        first_name="Asha",
        last_name="Rai",
        age=30,
        gender="female",
        primary_language="Nepali",
        other_languages=["English"],
        hometown="Pokhara",
    )
    session = TeachingSession(id=str(uuid.uuid4()), teacher_id=teacher.id, register_used="tapai")
    message = Message(
        id=str(uuid.uuid4()),
        session_id=session.id,
        teacher_id=teacher.id,
        turn_index=0,
        role="teacher",
        text="नमस्ते भनेको hello हो",
        detected_language="ne",
        stt_confidence=0.91,
    )
    db_session.add_all([teacher, session, message])
    await db_session.flush()

    prep = keyterm_service_svc.KeytermPreparation()
    repair = transcript_repair_svc.TranscriptRepairResult(
        original_text=message.text,
        repaired_text=message.text,
        confidence_after=0.91,
    )
    analysis = turn_intelligence_svc.analyze_turn(
        hearing=_hearing(message.text, language="ne", mode="mixed"),
        repaired_transcript=repair,
        keyterms=prep,
        memory_context={},
    )
    await turn_intelligence_svc.persist_turn_intelligence(
        db_session,
        message_id=message.id,
        session_id=session.id,
        teacher_id=teacher.id,
        transcript_original=message.text,
        transcript_final=message.text,
        intelligence=analysis,
    )
    await db_session.commit()

    saved_analysis = (await db_session.execute(select(MessageAnalysis))).scalar_one()
    saved_entities = (await db_session.execute(select(MessageEntity))).scalars().all()

    assert saved_analysis.intent_label == analysis.intent.label
    assert saved_analysis.learning_weight == analysis.learning_weight
    assert len(saved_entities) >= 1


@pytest.mark.asyncio
async def test_dashboard_overview_includes_turn_intelligence(client, db_session, demo_token):
    teacher = User(
        id="d0000000-0000-0000-0000-000000000001",
        email="teacher@example.com",
        first_name="Asha",
        last_name="Rai",
        age=30,
        gender="female",
        primary_language="Nepali",
        other_languages=["English"],
        hometown="Pokhara",
    )
    session = TeachingSession(id=str(uuid.uuid4()), teacher_id=teacher.id, register_used="tapai")
    teacher_message = Message(
        id=str(uuid.uuid4()),
        session_id=session.id,
        teacher_id=teacher.id,
        turn_index=0,
        role="teacher",
        text="नमस्ते भनेको hello हो",
        detected_language="ne",
        stt_confidence=0.91,
    )
    lipi_message = Message(
        id=str(uuid.uuid4()),
        session_id=session.id,
        teacher_id=teacher.id,
        turn_index=1,
        role="lipi",
        text="नमस्ते भनेको hello हो, है?",
    )
    db_session.add_all([teacher, session, teacher_message, lipi_message])
    await db_session.flush()

    prep = keyterm_service_svc.KeytermPreparation()
    repair = transcript_repair_svc.TranscriptRepairResult(
        original_text=teacher_message.text,
        repaired_text=teacher_message.text,
        confidence_after=0.91,
    )
    analysis = turn_intelligence_svc.analyze_turn(
        hearing=_hearing(teacher_message.text, language="ne", mode="mixed"),
        repaired_transcript=repair,
        keyterms=prep,
        memory_context={},
    )
    await turn_intelligence_svc.persist_turn_intelligence(
        db_session,
        message_id=teacher_message.id,
        session_id=session.id,
        teacher_id=teacher.id,
        transcript_original=teacher_message.text,
        transcript_final=teacher_message.text,
        intelligence=analysis,
    )
    await db_session.commit()

    response = await client.get(
        "/api/dashboard/overview",
        headers={"Authorization": f"Bearer {demo_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "turn_intelligence" in payload
    assert "intent_distribution" in payload["turn_intelligence"]
    assert payload["turn_intelligence"]["recent_turns"]
