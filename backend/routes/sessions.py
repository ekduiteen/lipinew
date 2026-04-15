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

from cache import valkey
from config import settings
from db.connection import SessionLocal
from dependencies.auth import get_ws_user
from models.session import TeachingSession
from services import llm as llm_svc
from services import stt as stt_svc
from services import tts as tts_svc
from services import points as points_svc
from services import badges as badges_svc
from services import message_store
from services import learning as learning_svc
from services import topic_memory as topic_memory_svc
from services.prompt_builder import (
    TeacherProfile,
    build_system_prompt,
    build_turn_guidance,
    Register,
)

router = APIRouter()
logger = logging.getLogger("lipi.backend.sessions")

_MSG_HISTORY_KEY = "session:{session_id}:messages"
_PROFILE_KEY = "user:{user_id}:tone_profile"
_MAX_CONTEXT_TURNS = 20


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _load_message_history(session_id: str) -> list[dict]:
    raw = await valkey.get(_MSG_HISTORY_KEY.format(session_id=session_id))
    return json.loads(raw) if raw else []


async def _save_message_history(session_id: str, messages: list[dict]) -> None:
    trimmed = messages[-(_MAX_CONTEXT_TURNS * 2):]
    await valkey.setex(
        _MSG_HISTORY_KEY.format(session_id=session_id),
        3600,
        json.dumps(trimmed),
    )


async def _load_tone_profile(user_id: str) -> TeacherProfile:
    raw = await valkey.get(_PROFILE_KEY.format(user_id=user_id))
    if raw:
        data = json.loads(raw)
        # Normalise: old cache format used first_name/last_name, new uses name
        if "name" not in data and ("first_name" in data or "last_name" in data):
            data["name"] = f"{data.pop('first_name', '')} {data.pop('last_name', '')}".strip() or "साथी"
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


# ─── REST: create session ────────────────────────────────────────────────────

@router.post("/api/sessions")
async def create_session(user_id: str = Depends(get_ws_user)) -> dict:
    """Create a new teaching session row and return the session_id."""
    session_id = str(uuid.uuid4())
    async with SessionLocal() as db:
        profile = await _load_tone_profile(user_id)
        db.add(TeachingSession(
            id=session_id,
            teacher_id=user_id,
            register_used=profile.register,
        ))
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
            await db.commit()

    # Track turn index in-memory for this connection
    turn_index = 0

    try:
        while True:
            # ── 1. Receive audio ──────────────────────────────────────────
            data = await websocket.receive()
            if "bytes" not in data:
                continue
            audio_bytes: bytes = data["bytes"]

            # ── 2. STT (OBSERVE) ─────────────────────────────────────────
            stt_t0 = time.monotonic()
            stt_result = await stt_svc.transcribe(audio_bytes, http)
            stt_ms = int((time.monotonic() - stt_t0) * 1000)

            teacher_text: str = stt_result["text"].strip()
            if not teacher_text:
                await websocket.send_json({"type": "empty_audio"})
                continue

            await websocket.send_json({
                "type": "transcript",
                "text": teacher_text,
                "language": stt_result.get("language"),
                "confidence": stt_result.get("confidence"),
            })

            logger.debug(
                "STT %dms: %r (lang=%s conf=%.2f)",
                stt_ms, teacher_text, stt_result["language"], stt_result["confidence"],
            )

            # ── 3. Register switch detection ──────────────────────────────
            new_register = _detect_register_switch(teacher_text, profile.register)
            if new_register and new_register != profile.register:
                profile.register = new_register
                system_prompt = build_system_prompt(profile)
                message_history[0] = {"role": "system", "content": system_prompt}
                logger.info("Register switched to %s", new_register)

            # ── 4. LLM (stream tokens to client) ─────────────────────────
            memory = await topic_memory_svc.load_session_memory(session_id)
            memory_block = topic_memory_svc.build_memory_block(memory)
            turn_guidance = build_turn_guidance(
                teacher_text,
                stt_result.get("language"),
                memory_block=memory_block,
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
            if lipi_text:
                await websocket.send_json({"type": "token", "text": lipi_text})
            if len(message_history) >= 2 and message_history[-2].get("content") == turn_guidance:
                message_history.pop()
                message_history.pop()
                message_history.append({"role": "user", "content": teacher_text})
            message_history.append({"role": "assistant", "content": lipi_text})
            await topic_memory_svc.update_session_memory(
                session_id,
                teacher_text=teacher_text,
                lipi_text=lipi_text,
                detected_language=stt_result.get("language"),
            )

            # ── 5. Correction detection ───────────────────────────────────
            is_correction = any(
                kw in lipi_text for kw in ["सही", "राम्रो", "हुन्छ", "correct", "well done"]
            )

            # ── 6. Persist messages to DB (both turns) ────────────────────
            async with SessionLocal() as db:
                current_turn = await message_store.get_turn_count(db, session_id)
                await message_store.persist_teacher_turn(
                    db,
                    session_id=session_id,
                    user_id=user_id,
                    turn_index=current_turn,
                    text=teacher_text,
                    detected_language=stt_result.get("language"),
                    stt_confidence=stt_result.get("confidence"),
                    audio_duration_ms=stt_result.get("duration_ms"),
                )
                await message_store.persist_lipi_turn(
                    db,
                    session_id=session_id,
                    user_id=user_id,
                    turn_index=current_turn + 1,
                    text=lipi_text,
                    llm_model=settings.vllm_model,
                    llm_latency_ms=llm_ms,
                )
                if is_correction:
                    streak = await points_svc.get_current_streak(db, user_id)
                    await points_svc.log_transaction(
                        db, user_id=user_id, session_id=session_id,
                        event_type="correction_accepted", current_streak=streak,
                    )
                await db.commit()

            turn_index += 2

            # ── 7. Valkey history (rolling LLM context) ───────────────────
            await _save_message_history(session_id, message_history)

            # ── 8. Learning cycle — durable queue, never blocks WS ─────────
            await learning_svc.enqueue_turn(
                session_id=session_id,
                user_id=user_id,
                teacher_text=teacher_text,
                lipi_response=lipi_text,
                stt_result=stt_result,
            )

            # ── 9. TTS → send audio ───────────────────────────────────────
            wav_bytes = await tts_svc.synthesize(lipi_text, http)
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
