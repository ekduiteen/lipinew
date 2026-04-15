"""
WebSocket conversation handler — /ws/session/{session_id}

Flow per turn:
  1. Receive audio bytes from client
  2. STT → text                               (OBSERVE)
  3. Build / load message history
  4. LLM → response text (streamed)
  5. TTS → WAV bytes
  6. Send WAV bytes + metadata back to client
  7. Persist teacher + LIPI turns to DB       (STORE)
  8. Queue learning cycle job                 (PROCESS → EXTRACT → STORE)

The client sends binary frames (raw audio) and receives binary frames (WAV)
interleaved with JSON text frames for metadata (corrections, points, state).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

import cache
from config import settings
from db.connection import SessionLocal, get_db
from dependencies.auth import get_ws_user, get_current_user_flexible
from models.curriculum import UserCurriculumProfile
from models.session import TeachingSession
from models.user import User
from services import llm as llm_svc
from services import stt as stt_svc
from services import tts as tts_svc
from services import points as points_svc
from services import badges as badges_svc
from services import audio_storage as audio_storage_svc
from services import curriculum as curriculum_svc
from services import diversity as diversity_svc
from services import hearing as hearing_svc
from services import input_understanding as input_understanding_svc
from services import message_store
from services import learning as learning_svc
from services import memory_service as memory_service_svc
from services import personality as personality_svc
from services import behavior_policy as behavior_policy_svc
from services import correction_graph as correction_graph_svc
from services import post_generation_guard as post_generation_guard_svc
from services import response_orchestrator as response_orchestrator_svc
from services import response_cleanup as response_cleanup_svc
from services import routing_hooks as routing_hooks_svc
from services import teacher_modeling as teacher_modeling_svc
from services import training_capture as training_capture_svc
from services import topic_memory as topic_memory_svc
from services import turn_interpreter as turn_interpreter_svc
from services.prompt_builder import (
    TeacherProfile,
    build_system_prompt,
    Register,
)

router = APIRouter()
logger = logging.getLogger("lipi.backend.sessions")

_MSG_HISTORY_KEY = "session:{session_id}:messages"
_PROFILE_KEY = "user:{user_id}:tone_profile"
_MAX_CONTEXT_TURNS = 20
# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _load_message_history(session_id: str) -> list[dict]:
    raw = await cache.valkey.get(_MSG_HISTORY_KEY.format(session_id=session_id))
    return json.loads(raw) if raw else []


async def _save_message_history(session_id: str, messages: list[dict]) -> None:
    trimmed = messages[-(_MAX_CONTEXT_TURNS * 2):]
    await cache.valkey.setex(
        _MSG_HISTORY_KEY.format(session_id=session_id),
        3600,
        json.dumps(trimmed),
    )


async def _load_tone_profile(user_id: str) -> TeacherProfile:
    raw = await cache.valkey.get(_PROFILE_KEY.format(user_id=user_id))
    if raw:
        data = json.loads(raw)
        # Normalise: old cache format used first_name/last_name, new uses name
        if "name" not in data and ("first_name" in data or "last_name" in data):
            data["name"] = f"{data.pop('first_name', '')} {data.pop('last_name', '')}".strip() or "साथी"
        if "other_languages" not in data:
            data["other_languages"] = []
        try:
            return TeacherProfile(**data)
        except TypeError:
            pass  # fall through to default below
    return TeacherProfile(
        name="साथी",
        age=25,
        gender="other",
        native_language="Nepali",
        city_or_village="Kathmandu",
        register="tapai",
        energy_level=3,
        humor_level=3,
        code_switch_ratio=0.2,
        session_phase=1,
        previous_topics=[],
        preferred_topics=[],
        other_languages=["English"],
    )


def _detect_register_switch(text: str, current: Register) -> Register | None:
    lower = text.lower()
    if "तँ भनेर बोल" in text or "ta bhanera bol" in lower:
        return "ta"
    if "तिमी भनेर बोल" in text or "timi bhanera bol" in lower:
        return "timi"
    if "तपाईं" in text and "भन्नुस्" in text:
        return "tapai"
    if "हजुर" in text and "भन्नुस्" in text:
        return "hajur"
    return None


def _extract_main_question(text: str) -> str | None:
    for chunk in text.replace("？", "?").split("?"):
        if chunk.strip():
            if "?" in text:
                return chunk.strip() + "?"
    sentences = [part.strip() for part in text.split("।") if part.strip()]
    if sentences:
        tail = sentences[-1]
        if any(token in tail.lower() for token in ("how", "what", "when", "why", "right")):
            return tail
    return None


# ─── REST: create session ────────────────────────────────────────────────────

@router.post("/api/sessions")
async def create_session(
    user_id: str = Depends(get_current_user_flexible),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new teaching session row and return the session_id."""
    session_id = str(uuid.uuid4())
    profile = await _load_tone_profile(user_id)
    user = await db.get(User, user_id)
    if user is not None:
        await curriculum_svc.get_or_create_user_profile(
            db,
            user,
            active_register=profile.register,
            code_switch_tendency=profile.code_switch_ratio,
        )
    db.add(TeachingSession(
        id=session_id,
        teacher_id=user_id,
        register_used=profile.register,
    ))
    if user is not None:
        streak = await points_svc.get_current_streak(db, user_id)
        await points_svc.log_transaction(
            db, user_id=user_id, session_id=session_id,
            event_type="session_base", current_streak=streak,
        )
    await db.commit()
    return {
        "session_id": session_id,
        "user_id": user_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── WebSocket endpoint ───────────────────────────────────────────────────────

@router.websocket("/ws/session/{session_id}")
async def conversation_ws(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Depends(get_ws_user),
):
    await websocket.accept()
    logger.info("WS connected session=%s user=%s", session_id, user_id)

    profile = await _load_tone_profile(user_id)
    system_prompt = build_system_prompt(profile)
    message_history: list[dict] = await _load_message_history(session_id)
    user: User | None = None
    curriculum_profile: UserCurriculumProfile | None = None

    if not message_history or message_history[0].get("role") != "system":
        message_history.insert(0, {"role": "system", "content": system_prompt})

    http = websocket.app.state.http

    # Ensure session row exists
    async with SessionLocal() as db:
        if not await db.get(TeachingSession, session_id):
            db.add(TeachingSession(
                id=session_id,
                teacher_id=user_id,
                register_used=profile.register,
            ))
        user = await db.get(User, user_id)
        if user is None:
            raise RuntimeError(f"User not found: {user_id}")
        curriculum_profile = await curriculum_svc.get_or_create_user_profile(
            db,
            user,
            active_register=profile.register,
            code_switch_tendency=profile.code_switch_ratio,
        )
        await db.commit()

    # Track turn index in-memory for this connection
    turn_index = 0

    try:
        MAX_AUDIO_FRAME_BYTES = 500_000  # 500 KB per frame — reject oversized frames

        while True:
            # ── 1. Receive audio ──────────────────────────────────────────
            data = await websocket.receive()
            if "bytes" not in data:
                continue
            audio_bytes: bytes = data["bytes"]

            # Guard against oversized frames (DoS protection)
            if len(audio_bytes) > MAX_AUDIO_FRAME_BYTES:
                logger.warning(
                    "Oversized audio frame rejected: %d bytes (session=%s)",
                    len(audio_bytes), session_id,
                )
                await websocket.send_json({"type": "error", "detail": "frame_too_large"})
                await websocket.close(code=1009, reason="frame too large")
                return

            # ── 2. STT (OBSERVE) ─────────────────────────────────────────
            stt_t0 = time.monotonic()
            stt_result = await stt_svc.transcribe(audio_bytes, http)
            stt_ms = int((time.monotonic() - stt_t0) * 1000)

            hearing = hearing_svc.analyze_hearing(stt_result)
            teacher_text: str = hearing.clean_text
            if not teacher_text:
                await websocket.send_json({"type": "empty_audio"})
                continue

            await websocket.send_json({
                "type": "transcript",
                "text": teacher_text,
                "language": hearing.language,
                "confidence": hearing.confidence,
                "mode": hearing.mode,
                "quality": hearing.quality_label,
            })

            logger.debug(
                "STT %dms: %r (lang=%s conf=%.2f)",
                stt_ms, teacher_text, stt_result["language"], stt_result["confidence"],
            )
            corrected_recently = curriculum_svc.detect_correction_signal(teacher_text)

            # ── 3. Register switch detection ──────────────────────────────
            new_register = _detect_register_switch(teacher_text, profile.register)
            if new_register and new_register != profile.register:
                profile.register = new_register
                system_prompt = build_system_prompt(profile)
                message_history[0] = {"role": "system", "content": system_prompt}
                logger.info("Register switched to %s", new_register)

            # ── 4. LLM (stream tokens to client) ─────────────────────────
            memory = await topic_memory_svc.load_session_memory(session_id)
            memory["latest_teacher_text"] = teacher_text
            interpretation = turn_interpreter_svc.interpret_turn(hearing, memory)
            understanding = input_understanding_svc.analyze_input(hearing, interpretation)
            async with SessionLocal() as db:
                if user is None:
                    user = await db.get(User, user_id)
                if user is None:
                    raise RuntimeError(f"User not found during planning: {user_id}")
                if curriculum_profile is None:
                    curriculum_profile = await curriculum_svc.get_or_create_user_profile(
                        db,
                        user,
                        active_register=profile.register,
                        code_switch_tendency=profile.code_switch_ratio,
                    )
                structured_memory = await memory_service_svc.load_session_memory(
                    db,
                    session_id=session_id,
                    teacher_id=user_id,
                )
                teacher_model = await teacher_modeling_svc.build_teacher_model(
                    db,
                    user=user,
                    profile=curriculum_profile,
                )
                correction_summary = await correction_graph_svc.get_recent_correction_summary(
                    db,
                    teacher_id=user_id,
                )

                previous_event = await curriculum_svc.resolve_latest_prompt_event(
                    db,
                    user_id=user_id,
                    session_id=session_id,
                    teacher_text=teacher_text,
                    stt_confidence=stt_result.get("confidence"),
                )
                if previous_event is not None:
                    topic_coverage = await curriculum_svc.get_or_create_topic_coverage(
                        db,
                        user_id=user_id,
                        topic_key=previous_event.topic_key,
                    )
                    topic_coverage.times_answered += 1
                    if previous_event.was_corrected:
                        topic_coverage.times_corrected += 1
                    topic_coverage.confidence_score = float(
                        previous_event.response_quality or topic_coverage.confidence_score or 0.5
                    )
                    await diversity_svc.refresh_global_coverage_for_event(
                        db,
                        topic_key=previous_event.topic_key,
                        register_key=previous_event.register_key,
                        language_key=previous_event.language_key,
                    )

                gap_scores = await diversity_svc.load_gap_scores(
                    db,
                    register_key=profile.register,
                    language_key=curriculum_svc.infer_language_key(
                        teacher_text,
                        hearing.language,
                    ),
                )
                plan = await curriculum_svc.plan_next_question(
                    db,
                    user=user,
                    user_profile=curriculum_profile,
                    session_state=memory,
                    turn_interpretation=interpretation,
                    register_key=profile.register,
                    gap_scores=gap_scores,
                    corrected_recently=corrected_recently,
                )
                curriculum_profile.conversation_turn_count += 1
                await curriculum_svc.sync_profile_after_plan(
                    db,
                    curriculum_profile,
                    plan,
                    corrected_recently=corrected_recently,
                )
                await db.commit()

            response_plan = personality_svc.build_response_plan(
                hearing,
                interpretation,
                plan,
                memory,
            )
            behavior_policy = behavior_policy_svc.choose_behavior_policy(
                teacher_model=teacher_model,
                session_memory=structured_memory,
                correction_count_recent=correction_summary.recent_count,
                understanding=understanding,
            )
            routing_hooks = routing_hooks_svc.build_routing_hooks(
                teacher_model=teacher_model,
                understanding=understanding,
                behavior_policy=behavior_policy,
            )
            clarification_only = not hearing.conversation_allowed or hearing.quality_label == "medium"
            llm_ms = 0
            if clarification_only:
                lipi_text = personality_svc.build_clarification_reply(hearing)
            elif interpretation.intent_type == "invite_lipi_choice":
                lipi_text = personality_svc.build_direct_choice_reply(
                    hearing,
                    plan,
                    target_language=profile.native_language,
                )
            else:
                response_package = response_orchestrator_svc.build_response_package(
                    teacher_text=teacher_text,
                    detected_language=hearing.language,
                    teacher_profile=profile,
                    teacher_model=teacher_model,
                    session_memory=structured_memory,
                    understanding=understanding,
                    behavior_policy=behavior_policy,
                    question_plan=plan,
                    response_plan=response_plan,
                )
                turn_guidance = response_package.turn_guidance + (
                    "## Routing hooks\n"
                    f"- Dialect adapter: {routing_hooks.dialect_adapter or 'none'}\n"
                    f"- Behavior adapter: {routing_hooks.behavior_adapter or 'none'}\n"
                    f"- STT bias: {routing_hooks.stt_bias or 'none'}\n"
                    f"- TTS voice profile: {routing_hooks.tts_voice_profile or 'none'}\n"
                    f"- Response ranker: {routing_hooks.response_ranker or 'none'}\n"
                )
                message_history.append({"role": "system", "content": turn_guidance})
                message_history.append({"role": "user", "content": teacher_text})
                llm_t0 = time.monotonic()
                try:
                    lipi_text = await llm_svc.generate_teacher_reply(
                        message_history,
                        http,
                        teacher_text=teacher_text,
                        detected_language=stt_result.get("language"),
                    )
                except httpx.TimeoutException:
                    logger.warning("LLM timeout session=%s turn=%s", session_id, turn_index // 2 + 1)
                    lipi_text = "माफ गर्नुहोस्, उत्तर दिन ढिलो भयो। फेरि छोटो गरी भन्नुहोस्।"
                except Exception as exc:
                    logger.warning("LLM reply error session=%s: %s", session_id, exc)
                    lipi_text = "माफ गर्नुहोस्, मैले ठिकसँग बुझिनँ। फेरि एकचोटि भन्नुहोस्।"
                llm_ms = int((time.monotonic() - llm_t0) * 1000)
                if len(message_history) >= 2 and message_history[-2].get("content") == turn_guidance:
                    message_history.pop()
                    message_history.pop()
                    message_history.append({"role": "user", "content": teacher_text})
            lipi_text = response_cleanup_svc.finalize_reply(lipi_text, hearing)
            guard_result = post_generation_guard_svc.guard_response(
                lipi_text,
                hearing=hearing,
                understanding=understanding,
                policy=behavior_policy,
            )
            lipi_text = response_cleanup_svc.finalize_reply(guard_result.text, hearing)
            if lipi_text:
                await websocket.send_json({"type": "token", "text": lipi_text})
            message_history.append({"role": "assistant", "content": lipi_text})
            await topic_memory_svc.update_session_memory(
                session_id,
                teacher_text=teacher_text,
                lipi_text=lipi_text,
                detected_language=hearing.language,
                last_question=_extract_main_question(lipi_text),
            )

            # ── 5. Correction detection ───────────────────────────────────
            is_correction = understanding.is_correction
            audio_path = await audio_storage_svc.store_teacher_audio(
                audio_bytes=audio_bytes,
                session_id=session_id,
                teacher_id=user_id,
                turn_index=turn_index,
            )

            # ── 6. Persist messages to DB (both turns) ────────────────────
            async with SessionLocal() as db:
                user_for_update = await db.get(User, user_id)
                if user_for_update is None:
                    raise RuntimeError(f"User not found during persistence: {user_id}")
                current_turn = await message_store.get_turn_count(db, session_id)
                teacher_capture = training_capture_svc.build_training_capture(
                    session_id=session_id,
                    teacher_id=user_id,
                    transcript=teacher_text,
                    stt_confidence=hearing.confidence,
                    audio_path=audio_path,
                    audio_duration_ms=stt_result.get("duration_ms"),
                    speaker_embedding=[],
                    understanding=understanding,
                    interpretation=interpretation,
                    behavior_policy=behavior_policy,
                )
                teacher_message = await message_store.persist_teacher_turn(
                    db,
                    session_id=session_id,
                    user_id=user_id,
                    turn_index=current_turn,
                    text=teacher_text,
                    detected_language=hearing.language,
                    audio_path=audio_path,
                    stt_confidence=hearing.confidence,
                    audio_duration_ms=stt_result.get("duration_ms"),
                    raw_signals_json=teacher_capture.raw_data,
                    derived_signals_json=teacher_capture.derived_signals,
                    high_value_signals_json=teacher_capture.high_value_signals,
                    style_signals_json=teacher_capture.style_signals,
                    prosody_signals_json=teacher_capture.prosody_signals,
                    nuance_signals_json=teacher_capture.nuance_signals,
                )
                lipi_message = await message_store.persist_lipi_turn(
                    db,
                    session_id=session_id,
                    user_id=user_id,
                    turn_index=current_turn + 1,
                    text=lipi_text,
                    llm_model=settings.vllm_model,
                    llm_latency_ms=llm_ms,
                    derived_signals_json={
                        "response_language": behavior_policy.response_language,
                        "dialect_alignment": behavior_policy.dialect_alignment,
                    },
                    style_signals_json={
                        "tone_style": behavior_policy.tone_style,
                        "politeness_level": behavior_policy.politeness_level,
                    },
                )
                previous_lipi_message = await correction_graph_svc.get_previous_lipi_message(
                    db,
                    session_id=session_id,
                    before_turn_index=current_turn,
                )
                correction_event_id: str | None = None
                if is_correction and previous_lipi_message is not None:
                    correction_event = await correction_graph_svc.record_correction_event(
                        db,
                        session_id=session_id,
                        teacher_id=user_id,
                        teacher_message=teacher_message,
                        wrong_message=previous_lipi_message,
                        corrected_claim=teacher_text,
                        correction_type=correction_graph_svc.infer_correction_type(teacher_text),
                        topic=understanding.topic,
                        language_key=understanding.primary_language,
                        confidence_before=0.35,
                        confidence_after=max(hearing.confidence, 0.75),
                    )
                    correction_event_id = correction_event.id
                    updated_high_value = dict(teacher_message.high_value_signals_json or {})
                    updated_high_value["correction_event_id"] = {
                        "value": correction_event_id,
                        "confidence": 1.0,
                        "source": "correction_graph_v1",
                    }
                    teacher_message.high_value_signals_json = updated_high_value
                await teacher_modeling_svc.record_teacher_signals(
                    db,
                    teacher_id=user_id,
                    session_id=session_id,
                    message_id=teacher_message.id,
                    understanding=understanding,
                )
                await teacher_modeling_svc.apply_teacher_turn_outcome(
                    db,
                    user=user_for_update,
                    understanding_is_correction=understanding.is_correction,
                    understanding_is_teaching=understanding.is_teaching,
                    transcript_confidence=understanding.transcript_confidence,
                    session_id=session_id,
                )
                await memory_service_svc.update_session_memory(
                    db,
                    session_id=session_id,
                    teacher_id=user_id,
                    turn_index=current_turn + 1,
                    existing=structured_memory,
                    active_language=understanding.primary_language,
                    active_topic=understanding.topic,
                    taught_terms=interpretation.taught_terms,
                    correction_text=teacher_text if understanding.is_correction else None,
                    misunderstanding_text=teacher_text if hearing.quality_label != "good" else None,
                    next_followup_goal=plan.question_type,
                    user_style=memory.get("user_style", "neutral"),
                    style_memory={
                        "tone": understanding.tone,
                        "register_estimate": understanding.register_estimate,
                        "speech_rate": understanding.speech_rate,
                        "pronunciation_style": understanding.pronunciation_style,
                        "prosody_pattern": understanding.prosody_pattern,
                        "dialect_guess": understanding.dialect_guess,
                    },
                )
                if is_correction:
                    streak = await points_svc.get_current_streak(db, user_id)
                    await points_svc.log_transaction(
                        db, user_id=user_id, session_id=session_id,
                        event_type="correction_accepted", current_streak=streak,
                    )
                if not clarification_only:
                    await curriculum_svc.record_prompt_event(
                        db,
                        user_id=user_id,
                        session_id=session_id,
                        plan=plan,
                    )
                await db.commit()

            turn_index += 2

            # ── 7. Valkey history (rolling LLM context) ───────────────────
            await _save_message_history(session_id, message_history)

            # ── 8. Learning cycle — durable queue, never blocks WS ─────────
            if not clarification_only:
                await learning_svc.enqueue_turn(
                session_id=session_id,
                user_id=user_id,
                teacher_text=teacher_text,
                lipi_response=lipi_text,
                stt_result=stt_result,
                hearing_result=hearing.to_dict(),
                turn_interpretation=interpretation.to_dict(),
                input_understanding=understanding.to_dict(),
                behavior_policy=behavior_policy.to_dict(),
                audio_path=audio_path,
                target_language=profile.native_language,
            )

            # ── 9. TTS → send audio ───────────────────────────────────────
            wav_bytes = await tts_svc.synthesize(lipi_text, http, language=hearing.language)
            await websocket.send_json({
                "type": "tts_start",
                "text": lipi_text,
                "turn": turn_index // 2,
                "is_correction": is_correction,
            })
            if not wav_bytes:
                await websocket.send_json({"type": "empty_audio"})
                await websocket.send_json({"type": "tts_end"})
                continue

            await websocket.send_bytes(wav_bytes)
            await websocket.send_json({"type": "tts_end"})

    except WebSocketDisconnect:
        logger.info("WS disconnected session=%s", session_id)
        await _close_session(session_id, user_id)
    except RuntimeError as exc:
        if 'disconnect message has been received' in str(exc):
            logger.info("WS disconnected during receive session=%s", session_id)
            await _close_session(session_id, user_id)
            return
        logger.exception("WS runtime error session=%s: %s", session_id, exc)
        await _close_session(session_id, user_id)
    except Exception as exc:
        logger.exception("WS error session=%s: %s", session_id, exc)
        await _close_session(session_id, user_id)
        try:
            await websocket.close(code=1011, reason="internal error")
        except RuntimeError:
            pass


async def _close_session(session_id: str, user_id: str) -> None:
    """Mark session ended, rebuild summary, check badges, bust leaderboard cache."""
    try:
        async with SessionLocal() as db:
            session = await db.get(TeachingSession, session_id)
            if session and not session.ended_at:
                session.ended_at = datetime.now(timezone.utc)
            await db.flush()
            await points_svc.rebuild_summary(db, user_id)
            new_badges = await badges_svc.check_and_award(db, user_id)
            await db.commit()
            if new_badges:
                logger.info("New badges user=%s: %s", user_id, [b.badge_id for b in new_badges])
        from routes.leaderboard import invalidate_leaderboard_cache
        await invalidate_leaderboard_cache()
    except Exception as exc:
        logger.warning("Session close error: %s", exc)
