from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from models.admin_control import AdminAccount
from models.curriculum import UserCurriculumProfile
from models.intelligence import (
    CorrectionEvent,
    KnowledgeConfidenceHistory,
    ReviewQueueItem,
    SessionMemorySnapshot,
    UsageRule,
)
from models.message import Message
from models.session import TeachingSession
from models.user import User
from services import admin_moderation as admin_moderation_svc
from services import learning as learning_svc
from services import memory_service as memory_service_svc
from services import response_orchestrator as response_orchestrator_svc
from services.behavior_policy import BehaviorPolicy
from services.curriculum import QuestionPlan
from services.input_understanding import InputUnderstanding
from services.personality import ResponsePlan
from services.prompt_builder import TeacherProfile
from services.teacher_modeling import TeacherModel


async def _seed_teacher(
    db_session,
    *,
    teacher_id: str,
    session_id: str,
    email: str,
) -> User:
    teacher = User(
        id=teacher_id,
        email=email,
        first_name="Teacher",
        last_name=teacher_id[-4:],
        age=35,
        gender="other",
        primary_language="Nepali",
        other_languages=["English"],
        hometown="Kathmandu",
    )
    session = TeachingSession(
        id=session_id,
        teacher_id=teacher_id,
        register_used="tapai",
    )
    profile = UserCurriculumProfile(
        user_id=teacher_id,
        primary_language="ne",
        active_register="tapai",
        code_switch_tendency=0.2,
        comfort_level=0.5,
        assigned_lane="basics_lane",
        conversation_turn_count=3,
    )
    db_session.add_all([teacher, session, profile])
    await db_session.flush()
    return teacher


@pytest.mark.asyncio
async def test_admin_approval_flips_flags_and_bumps_confidence(db_session):
    teacher_id = "d0000000-0000-0000-0000-000000000101"
    session_id = str(uuid.uuid4())
    await _seed_teacher(
        db_session,
        teacher_id=teacher_id,
        session_id=session_id,
        email="approval-teacher@example.com",
    )
    admin = AdminAccount(
        id="a0000000-0000-0000-0000-000000000001",
        email="admin@example.com",
        full_name="Moderator",
        role="moderator",
        is_active=True,
    )
    teacher_message = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        teacher_id=teacher_id,
        turn_index=2,
        role="teacher",
        text="Say भात, not rice.",
        detected_language="ne",
        raw_signals_json={},
        derived_signals_json={},
        high_value_signals_json={},
        style_signals_json={},
        prosody_signals_json={},
        nuance_signals_json={},
        stt_confidence=0.93,
    )
    correction_event = CorrectionEvent(
        id=str(uuid.uuid4()),
        session_id=session_id,
        teacher_id=teacher_id,
        wrong_message_id=None,
        correction_message_id=teacher_message.id,
        wrong_claim="rice",
        corrected_claim="भात",
        correction_type="replacement",
        confidence_before=0.4,
        confidence_after=0.8,
        topic="food_cooking",
        language_key="ne",
        is_approved=False,
    )
    usage_rule = UsageRule(
        id=str(uuid.uuid4()),
        teacher_id=teacher_id,
        session_id=session_id,
        correction_event_id=correction_event.id,
        topic_key="food_cooking",
        language_key="ne",
        rule_type="correction_rule",
        rule_text="Use भात instead of rice.",
        source_text="rice",
        confidence=0.7,
        is_approved=False,
    )
    review_item = ReviewQueueItem(
        id=str(uuid.uuid4()),
        source_audio_path="audio.wav",
        source_transcript="Say bhat, not rice",
        teacher_id=teacher_id,
        session_id=session_id,
        extracted_claim="भात",
        extraction_metadata={
            "correction_event_id": correction_event.id,
            "usage_rule_id": usage_rule.id,
            "message_id": teacher_message.id,
            "language_key": "ne",
        },
        confidence=0.8,
        model_source="test",
        status="pending_review",
    )
    db_session.add_all([admin, teacher_message, correction_event, usage_rule, review_item])
    await db_session.commit()

    gold = await admin_moderation_svc.label_and_promote_to_gold(
        db=db_session,
        item_id=review_item.id,
        admin=admin,
        corrected_transcript="भात",
        dialect="kathmandu",
    )

    await db_session.refresh(correction_event)
    await db_session.refresh(usage_rule)
    await db_session.refresh(review_item)

    history_rows = (
        await db_session.execute(
            select(KnowledgeConfidenceHistory).where(
                KnowledgeConfidenceHistory.correction_event_id == correction_event.id
            )
        )
    ).scalars().all()

    assert gold.corrected_transcript == "भात"
    assert correction_event.is_approved is True
    assert usage_rule.is_approved is True
    assert review_item.status == "approved"
    assert history_rows[-1].new_confidence == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_cross_session_memory_loads_latest_snapshot(db_session):
    teacher_id = "d0000000-0000-0000-0000-000000000102"
    session_id = str(uuid.uuid4())
    await _seed_teacher(
        db_session,
        teacher_id=teacher_id,
        session_id=session_id,
        email="memory-teacher@example.com",
    )
    snapshot = SessionMemorySnapshot(
        id=str(uuid.uuid4()),
        session_id=session_id,
        teacher_id=teacher_id,
        turn_index=4,
        active_language="ne",
        active_topic="food_cooking",
        recent_taught_words=["भात", "पानी", "दाल"],
        recent_corrections=["Say भात instead of rice."],
        unresolved_misunderstandings=[],
        next_followup_goal="when_is_this_used",
        user_style="formal",
        style_memory_json={"register_estimate": "tapai", "speech_rate": "medium"},
    )
    db_session.add(snapshot)
    await db_session.commit()

    memory = await memory_service_svc.load_teacher_long_term_memory(
        db_session,
        teacher_id=teacher_id,
    )

    assert memory.active_topic == "food_cooking"
    assert memory.recent_taught_words[-2:] == ["पानी", "दाल"]
    assert memory.recent_corrections[-1] == "Say भात instead of rice."


def test_response_package_includes_approved_rules():
    teacher_profile = TeacherProfile(
        name="Sathi",
        age=30,
        gender="other",
        native_language="Nepali",
        city_or_village="Kathmandu",
        register="tapai",
        energy_level=3,
        humor_level=2,
        code_switch_ratio=0.2,
        session_phase=1,
        previous_topics=["भात"],
        preferred_topics=["food_cooking"],
        other_languages=["English"],
    )
    teacher_model = TeacherModel(
        teacher_id="t1",
        credibility_score=0.8,
        correction_density=0.2,
        preferred_register="tapai",
        teaching_style="steady_teacher",
        expertise_domains=["food_cooking"],
        primary_languages=["Nepali"],
        language_mix={"ne": 3},
        dialect_signature_hook=None,
        dialect_tendencies=["kathmandu"],
        consistency_score=0.8,
        reliability_hook="high_trust",
    )
    session_memory = memory_service_svc.StructuredSessionMemory(
        active_language="ne",
        active_topic="food_cooking",
        recent_taught_words=["भात"],
        recent_corrections=["Use भात instead of rice."],
        unresolved_misunderstandings=[],
        next_followup_goal="when_is_this_used",
        user_style="formal",
        style_memory={"register_estimate": "tapai"},
    )
    understanding = InputUnderstanding(
        turn_id="turn-1",
        primary_language="ne",
        secondary_languages=[],
        code_switch_ratio=0.0,
        topic="food_cooking",
        tone="friendly",
        emotion="neutral",
        is_correction=True,
        is_teaching=True,
        taught_terms=["भात"],
        register_estimate="tapai",
        dialect_guess=None,
        dialect_confidence=0.0,
        speech_rate="medium",
        prosody_pattern="neutral",
        pronunciation_style="standard_spoken",
        transcript_confidence=0.92,
        learning_allowed=True,
        conversation_allowed=True,
        signal_confidences={"stt": 0.92},
    )
    behavior_policy = BehaviorPolicy(
        response_language="ne",
        mirror_code_switching=False,
        register="tapai",
        tone_style="respectful_accepting",
        uncertainty_level=0.08,
        curiosity_level=0.75,
        confirmation_style="correction_accept",
        max_followups=1,
        allowed_humor=0.05,
        infer_vs_ask="infer",
        dialect_alignment="neutral",
        politeness_level="high",
    )
    question_plan = QuestionPlan(
        topic_key="food_cooking",
        question_type="when_is_this_used",
        register_key="tapai",
        reason="recent correction",
        priority_score=0.9,
        fallback_question_type="example_request",
        assigned_lane="basics_lane",
        language_key="ne",
    )
    response_plan = ResponsePlan(
        acknowledgement="Accept the correction briefly.",
        learned_point="भात",
        question_goal="Ask about usage.",
        question_type="when_is_this_used",
        tone_style="warm_respectful",
        max_sentences=2,
        must_confirm=False,
        must_ask_repeat=False,
    )
    approved_rule = UsageRule(
        id=str(uuid.uuid4()),
        teacher_id="t1",
        session_id=str(uuid.uuid4()),
        correction_event_id=None,
        topic_key="food_cooking",
        language_key="ne",
        rule_type="correction_rule",
        rule_text="Use भात instead of rice.",
        source_text="rice",
        confidence=0.95,
        is_approved=True,
    )

    package = response_orchestrator_svc.build_response_package(
        teacher_text="भात कहिले भन्छन्?",
        detected_language="ne",
        teacher_profile=teacher_profile,
        teacher_model=teacher_model,
        session_memory=session_memory,
        understanding=understanding,
        behavior_policy=behavior_policy,
        question_plan=question_plan,
        response_plan=response_plan,
        approved_rules=[approved_rule],
    )

    assert "Approved prior teachings from this teacher" in package.turn_guidance
    assert "Use भात instead of rice." in package.turn_guidance


def test_validate_extraction_rejects_script_mismatch():
    is_valid, reason = learning_svc._validate_extraction(
        word="rice",
        language="ne",
        teacher_text="मैले भात खाएँ",
    )

    assert is_valid is False
    assert reason == "script_mismatch"


@pytest.mark.asyncio
async def test_low_trust_extraction_flagged_and_confidence_requires_multiple_teachers(db_session, monkeypatch):
    teacher1_id = "d0000000-0000-0000-0000-000000000103"
    teacher2_id = "d0000000-0000-0000-0000-000000000104"
    session1_id = str(uuid.uuid4())
    session2_id = str(uuid.uuid4())
    await _seed_teacher(
        db_session,
        teacher_id=teacher1_id,
        session_id=session1_id,
        email="teacher-one@example.com",
    )
    await _seed_teacher(
        db_session,
        teacher_id=teacher2_id,
        session_id=session2_id,
        email="teacher-two@example.com",
    )

    import services.points as points_svc

    async def _fake_streak(db, user_id):  # noqa: ARG001
        return 1

    async def _fake_log(*args, **kwargs):  # noqa: ARG001
        return None

    monkeypatch.setattr(points_svc, "get_current_streak", _fake_streak)
    monkeypatch.setattr(points_svc, "log_transaction", _fake_log)

    low_trust_count = await learning_svc._flag_low_trust_extraction(
        db=db_session,
        teacher_id=teacher1_id,
        session_id=session1_id,
        teacher_text="मैले भात खाएँ",
        word="rice",
        language="ne",
        reason="script_mismatch",
        stt_confidence=0.91,
        audio_path=None,
    )

    await learning_svc._upsert_vocabulary(
        db=db_session,
        word="भात",
        language="ne",
        definition_en="rice",
        user_id=teacher1_id,
        session_id=session1_id,
        stt_confidence=0.96,
    )
    await learning_svc._upsert_vocabulary(
        db=db_session,
        word="भात",
        language="ne",
        definition_en="rice",
        user_id=teacher1_id,
        session_id=session1_id,
        stt_confidence=0.96,
    )
    await learning_svc._upsert_vocabulary(
        db=db_session,
        word="भात",
        language="ne",
        definition_en="rice",
        user_id=teacher1_id,
        session_id=session1_id,
        stt_confidence=0.96,
    )

    confidence_single_teacher = (
        await db_session.execute(
            text("SELECT confidence FROM vocabulary_entries WHERE word = :word AND language = :language"),
            {"word": "भात", "language": "ne"},
        )
    ).scalar_one()

    await learning_svc._upsert_vocabulary(
        db=db_session,
        word="भात",
        language="ne",
        definition_en="rice",
        user_id=teacher2_id,
        session_id=session2_id,
        stt_confidence=0.96,
    )
    await db_session.commit()

    confidence_multi_teacher = (
        await db_session.execute(
            text("SELECT confidence FROM vocabulary_entries WHERE word = :word AND language = :language"),
            {"word": "भात", "language": "ne"},
        )
    ).scalar_one()
    review_items = (
        await db_session.execute(
            select(ReviewQueueItem).where(ReviewQueueItem.model_source == "learning_validation_guard")
        )
    ).scalars().all()

    assert low_trust_count == 1
    assert len(review_items) == 1
    assert review_items[0].extraction_metadata["reason"] == "script_mismatch"
    assert float(confidence_single_teacher) <= 0.70
    assert float(confidence_multi_teacher) > 0.70
