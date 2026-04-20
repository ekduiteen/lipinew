from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from models.curriculum import UserCurriculumProfile
from models.intelligence import TeacherSignal
from models.message import Message
from models.session import TeachingSession
from models.user import User
from services import behavior_policy as behavior_policy_svc
from services import correction_graph as correction_graph_svc
from services import input_understanding as input_understanding_svc
from services import memory_service as memory_service_svc
from services import post_generation_guard as post_generation_guard_svc
from services import teacher_modeling as teacher_modeling_svc
from services import training_capture as training_capture_svc
from services.hearing import HearingResult
from services.turn_interpreter import interpret_turn


async def _seed_teacher_and_session(db_session):
    teacher = User(
        id="d0000000-0000-0000-0000-000000000001",
        email="teacher@example.com",
        first_name="Abhi",
        last_name="Shrestha",
        age=41,
        gender="male",
        primary_language="Newar",
        other_languages=["English", "Nepali"],
        hometown="Kathmandu",
    )
    session = TeachingSession(
        id=str(uuid.uuid4()),
        teacher_id=teacher.id,
        register_used="tapai",
    )
    profile = UserCurriculumProfile(
        user_id=teacher.id,
        primary_language="new",
        active_register="tapai",
        code_switch_tendency=0.2,
        comfort_level=0.55,
        assigned_lane="regional_lane",
        conversation_turn_count=3,
    )
    db_session.add_all([teacher, session, profile])
    await db_session.flush()
    return teacher, session, profile


def _hearing(
    text: str,
    *,
    language: str = "en",
    confidence: float = 0.9,
    mode: str = "english",
    quality: str = "good",
    duration_ms: int | None = 2200,
) -> HearingResult:
    return HearingResult(
        raw_text=text,
        clean_text=text,
        confidence=confidence,
        language=language,
        mode=mode,
        quality_label=quality,
        audio_quality_score=confidence,
        audio_duration_ms=duration_ms,
        conversation_allowed=quality != "low",
        learning_allowed=quality == "good",
        reason_codes=[],
    )


class TestInputUnderstanding:
    def test_detects_correction_code_switch_and_nuance_signals(self):
        hearing = _hearing(
            "No, not like that. Newari ma jojolopa bhancha.",
            language="en",
            mode="mixed",
            confidence=0.88,
            duration_ms=1800,
        )
        interpretation = interpret_turn(hearing, {"user_style": "formal"})

        result = input_understanding_svc.analyze_input(hearing, interpretation)

        assert result.is_correction is True
        assert result.primary_language == "new"
        assert "en" in result.secondary_languages
        assert result.code_switch_ratio > 0
        assert result.dialect_guess == "newari_kathmandu_mix"
        assert result.speech_rate in {"medium", "fast"}
        assert result.pronunciation_style == "newari_leaning"


class TestBehaviorPolicy:
    @pytest.mark.asyncio
    async def test_prefers_ask_when_uncertain(self, db_session):
        teacher, _, profile = await _seed_teacher_and_session(db_session)
        teacher_model = await teacher_modeling_svc.build_teacher_model(db_session, user=teacher, profile=profile)
        memory = memory_service_svc.StructuredSessionMemory(
            active_language="new",
            active_topic="greeting_usage",
            recent_taught_words=["jojolopa"],
            recent_corrections=[],
            unresolved_misunderstandings=["previous greeting mismatch"],
            next_followup_goal="how_would_you_say",
            user_style="formal",
            style_memory={"register_estimate": "tapai"},
        )
        hearing = _hearing("How do you say hello in Newari?", confidence=0.66, quality="medium")
        interpretation = interpret_turn(hearing, {"user_style": "formal"})
        understanding = input_understanding_svc.analyze_input(hearing, interpretation)

        policy = behavior_policy_svc.choose_behavior_policy(
            teacher_model=teacher_model,
            session_memory=memory,
            correction_count_recent=1,
            understanding=understanding,
            target_language="Newari",
            recent_assistant_replies=["How would you say that naturally?"],
        )

        assert policy.infer_vs_ask == "ask"
        assert policy.max_followups == 1
        assert policy.confirmation_style in {"repair", "inference_first"}
        assert policy.politeness_level == "high"
        assert policy.turn_goal in {"ELICIT_TARGET", "CLARIFY_MEANING"}


class TestSessionMemory:
    @pytest.mark.asyncio
    async def test_updates_and_persists_memory_snapshot(self, db_session, mock_valkey, monkeypatch):
        teacher, session, _ = await _seed_teacher_and_session(db_session)
        monkeypatch.setattr(memory_service_svc, "valkey", mock_valkey)

        existing = memory_service_svc.StructuredSessionMemory(
            active_language="ne",
            active_topic="everyday_basics",
            recent_taught_words=["namaste"],
            recent_corrections=[],
            unresolved_misunderstandings=[],
            next_followup_goal=None,
            user_style="neutral",
            style_memory={},
        )

        updated = await memory_service_svc.update_session_memory(
            db_session,
            session_id=session.id,
            teacher_id=teacher.id,
            turn_index=2,
            existing=existing,
            active_language="new",
            active_topic="greeting_usage",
            taught_terms=["jojolopa"],
            correction_text="Not like that, say jojolopa.",
            misunderstanding_text=None,
            next_followup_goal="when_is_this_used",
            user_style="formal",
            style_memory={"speech_rate": "medium", "dialect_guess": "newari_kathmandu_mix"},
        )

        assert updated.active_language == "new"
        assert "jojolopa" in updated.recent_taught_words
        assert updated.recent_corrections[-1] == "Not like that, say jojolopa."
        assert updated.style_memory["dialect_guess"] == "newari_kathmandu_mix"
        assert mock_valkey.setex.await_count == 1


class TestPostGenerationGuard:
    def test_rewrites_weak_student_reply(self):
        hearing = _hearing("Teach me what you want to learn", language="en")
        interpretation = interpret_turn(hearing, {})
        understanding = input_understanding_svc.analyze_input(hearing, interpretation)
        policy = behavior_policy_svc.BehaviorPolicy(
            conversation_language="en",
            teach_language="new",
            response_language="en",
            target_language_present=False,
            reply_mode="teach",
            steer_to_target_language=True,
            steering_strength="soft",
            turn_goal="ELICIT_TARGET",
            prompt_family="ask_natural_way",
            elicitation_goal="phrase",
            confirmation_goal="none",
            should_expand=False,
            should_ask_followup=True,
            handle_unclear_expression=False,
            unclear_expression_strategy="defer",
            mirror_code_switching=False,
            register="tapai",
            tone_style="curious_warm",
            uncertainty_level=0.1,
            curiosity_level=0.8,
            confirmation_style="light_ack",
            max_followups=1,
            allowed_humor=0.1,
            infer_vs_ask="infer",
            dialect_alignment="neutral",
            politeness_level="high",
        )

        result = post_generation_guard_svc.guard_response(
            "That is very interesting and you are teaching me more about this.",
            hearing=hearing,
            understanding=understanding,
            policy=policy,
        )

        assert result.action == "rewrite"
        assert "natural way" in result.text.lower()

    def test_keeps_specific_content_when_only_followup_is_generic(self):
        hearing = _hearing("Jojolopa means hello", language="en")
        interpretation = interpret_turn(hearing, {})
        understanding = input_understanding_svc.analyze_input(hearing, interpretation)
        policy = behavior_policy_svc.BehaviorPolicy(
            conversation_language="en",
            teach_language="new",
            response_language="ne",
            target_language_present=True,
            reply_mode="student",
            steer_to_target_language=False,
            steering_strength="none",
            turn_goal="CONFIRM_AND_EXPAND",
            prompt_family="confirm_meaning",
            elicitation_goal="none",
            confirmation_goal="meaning_check",
            should_expand=True,
            should_ask_followup=True,
            handle_unclear_expression=False,
            unclear_expression_strategy="defer",
            mirror_code_switching=False,
            register="tapai",
            tone_style="curious_warm",
            uncertainty_level=0.1,
            curiosity_level=0.8,
            confirmation_style="light_ack",
            max_followups=1,
            allowed_humor=0.1,
            infer_vs_ask="infer",
            dialect_alignment="neutral",
            politeness_level="high",
        )

        result = post_generation_guard_svc.guard_response(
            "जोजोलोपा भनेको अभिवादन हो। अरू के सिकाउँछौ?",
            hearing=hearing,
            understanding=understanding,
            policy=policy,
        )

        assert result.action == "approve"
        assert result.text == "जोजोलोपा भनेको अभिवादन हो।"


class TestTeacherCredibility:
    @pytest.mark.asyncio
    async def test_updates_teacher_credibility_on_correction(self, db_session):
        teacher, session, _ = await _seed_teacher_and_session(db_session)
        previous_score = teacher.credibility_score

        new_score = await teacher_modeling_svc.apply_teacher_turn_outcome(
            db_session,
            user=teacher,
            understanding_is_correction=True,
            understanding_is_teaching=True,
            transcript_confidence=0.92,
            session_id=session.id,
        )

        assert new_score > previous_score


class TestTrainingCapture:
    def test_builds_three_layer_training_payload(self):
        hearing = _hearing("Jojolopa means hello.", language="en", mode="mixed", confidence=0.91, duration_ms=1400)
        interpretation = interpret_turn(hearing, {"user_style": "formal"})
        understanding = input_understanding_svc.analyze_input(hearing, interpretation)
        policy = behavior_policy_svc.BehaviorPolicy(
            conversation_language="mixed",
            teach_language="new",
            response_language="ne",
            target_language_present=True,
            reply_mode="student",
            steer_to_target_language=False,
            steering_strength="none",
            turn_goal="CONFIRM_AND_EXPAND",
            prompt_family="confirm_meaning",
            elicitation_goal="none",
            confirmation_goal="meaning_check",
            should_expand=True,
            should_ask_followup=True,
            handle_unclear_expression=False,
            unclear_expression_strategy="defer",
            mirror_code_switching=True,
            register="tapai",
            tone_style="curious_warm",
            uncertainty_level=0.1,
            curiosity_level=0.9,
            confirmation_style="light_ack",
            max_followups=1,
            allowed_humor=0.05,
            infer_vs_ask="infer",
            dialect_alignment="newari_kathmandu_mix",
            politeness_level="high",
        )

        envelope = training_capture_svc.build_training_capture(
            session_id="s1",
            teacher_id="t1",
            transcript=hearing.clean_text,
            stt_confidence=hearing.confidence,
            audio_path="raw-teacher-audio/t1/s1/sample.bin",
            audio_duration_ms=hearing.audio_duration_ms,
            speaker_embedding=[],
            understanding=understanding,
            interpretation=interpretation,
            behavior_policy=policy,
            taught_words=["jojolopa"],
        )

        assert envelope.raw_data["audio_path"] == "raw-teacher-audio/t1/s1/sample.bin"
        assert envelope.derived_signals["dialect_guess"]["value"] == "newari_kathmandu_mix"
        assert envelope.high_value_signals["taught_words"]["value"] == ["jojolopa"]
        assert envelope.style_signals["politeness_level"]["value"] == "high"


class TestTeacherSignals:
    @pytest.mark.asyncio
    async def test_logs_teacher_signals(self, db_session):
        teacher, session, profile = await _seed_teacher_and_session(db_session)
        hearing = _hearing("Jojolopa bhancha.", language="en", mode="mixed", confidence=0.88)
        interpretation = interpret_turn(hearing, {"user_style": "formal"})
        understanding = input_understanding_svc.analyze_input(hearing, interpretation)

        await teacher_modeling_svc.record_teacher_signals(
            db_session,
            teacher_id=teacher.id,
            session_id=session.id,
            message_id=None,
            understanding=understanding,
        )

        signals = (await db_session.execute(select(TeacherSignal).where(TeacherSignal.teacher_id == teacher.id))).scalars().all()
        assert len(signals) >= 4


class TestServiceLevelTurnFlow:
    @pytest.mark.asyncio
    async def test_end_to_end_intelligence_turn_flow(self, db_session, mock_valkey, monkeypatch):
        teacher, session, profile = await _seed_teacher_and_session(db_session)
        monkeypatch.setattr(memory_service_svc, "valkey", mock_valkey)

        wrong_message = Message(
            id=str(uuid.uuid4()),
            session_id=session.id,
            teacher_id=teacher.id,
            turn_index=1,
            role="lipi",
            text="नमस्ते भनेको सधैं सबै ठाउँमा एउटै हो।",
        )
        teacher_message = Message(
            id=str(uuid.uuid4()),
            session_id=session.id,
            teacher_id=teacher.id,
            turn_index=2,
            role="teacher",
            text="होइन, जोजोलोपा नेवारी अभिवादन हो।",
            detected_language="ne",
            stt_confidence=0.91,
        )
        db_session.add_all([wrong_message, teacher_message])
        await db_session.flush()

        hearing = _hearing(teacher_message.text, language="ne", mode="nepali", confidence=0.91)
        interpretation = interpret_turn(hearing, {"user_style": "formal"})
        understanding = input_understanding_svc.analyze_input(hearing, interpretation)
        teacher_model = await teacher_modeling_svc.build_teacher_model(db_session, user=teacher, profile=profile)
        memory = memory_service_svc.StructuredSessionMemory(
            active_language="new",
            active_topic="greeting_usage",
            recent_taught_words=[],
            recent_corrections=[],
            unresolved_misunderstandings=[],
            next_followup_goal=None,
            user_style="formal",
            style_memory={},
        )
        policy = behavior_policy_svc.choose_behavior_policy(
            teacher_model=teacher_model,
            session_memory=memory,
            correction_count_recent=0,
            understanding=understanding,
            target_language="Newari",
            recent_assistant_replies=[],
        )

        correction_event = await correction_graph_svc.record_correction_event(
            db_session,
            session_id=session.id,
            teacher_id=teacher.id,
            teacher_message=teacher_message,
            wrong_message=wrong_message,
            corrected_claim=teacher_message.text,
            correction_type=correction_graph_svc.infer_correction_type(teacher_message.text),
            topic=understanding.topic,
            language_key=understanding.primary_language,
            confidence_before=0.35,
            confidence_after=0.9,
        )
        updated_memory = await memory_service_svc.update_session_memory(
            db_session,
            session_id=session.id,
            teacher_id=teacher.id,
            turn_index=2,
            existing=memory,
            active_language=understanding.primary_language,
            active_topic=understanding.topic,
            taught_terms=interpretation.taught_terms,
            correction_text=teacher_message.text,
            misunderstanding_text=None,
            next_followup_goal="contrast_request",
            user_style="formal",
            style_memory={"tone": understanding.tone, "speech_rate": understanding.speech_rate},
        )
        await teacher_modeling_svc.record_teacher_signals(
            db_session,
            teacher_id=teacher.id,
            session_id=session.id,
            message_id=teacher_message.id,
            understanding=understanding,
        )
        guard_result = post_generation_guard_svc.guard_response(
            "ठिक छ। साथीहरूले जोजोलोपा पनि भन्छन्?",
            hearing=hearing,
            understanding=understanding,
            policy=policy,
        )
        signals = (await db_session.execute(select(TeacherSignal).where(TeacherSignal.teacher_id == teacher.id))).scalars().all()

        assert correction_event.wrong_message_id == wrong_message.id
        assert updated_memory.active_topic == understanding.topic
        assert updated_memory.style_memory["speech_rate"] == understanding.speech_rate
        assert guard_result.action == "approve"
        assert len(signals) >= 4
