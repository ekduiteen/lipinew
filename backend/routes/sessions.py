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
import os
import time
import uuid
from dataclasses import replace
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, WebSocket, WebSocketDisconnect
import httpx
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import cache
from config import settings
from db.connection import SessionLocal, get_db
from dependencies.auth import get_ws_user, get_current_user_flexible
from models.message import Message
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
from services import audio_understanding as audio_understanding_svc
from services import message_store
from services import learning as learning_svc
from services import keyterm_service as keyterm_service_svc
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
from services import transcript_repair as transcript_repair_svc
from services import topic_memory as topic_memory_svc
from services import turn_intelligence as turn_intelligence_svc
from services import turn_interpreter as turn_interpreter_svc
from services.country_registry import get_base_asr_languages, load_country_profile, validate_country_target_language
from services.language_registry import get_normalization_rules, load_language_profile
from services.text_normalization import normalize_text_for_training
from services.asr_error_classifier import classify_asr_error
from services.data_quality import assign_training_tier
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
_TEACHING_MODES = {
    "free_conversation",
    "phrase_recording",
    "correction_mode",
    "storytelling",
    "ritual_cultural_words",
    "household_speech",
    "proverbs_idioms",
    "translation_teaching",
    "pronunciation_practice",
    "code_switch_practice",
}
# ─── Helpers ─────────────────────────────────────────────────────────────────


class SessionCreateRequest(BaseModel):
    country_code: str = "NP"
    target_language: str = "newari"
    bridge_language: str = "ne"
    script: str = "devanagari"
    dialect_label: str | None = None
    teaching_mode: str = "correction_mode"
    allow_code_switching: bool = True
    consent_training_use: bool = False


class CorrectionRequest(BaseModel):
    action: str
    transcript: str | None = None
    meaning_nepali: str | None = None
    meaning_english: str | None = None


def _build_session_language_contract(
    payload: SessionCreateRequest,
    *,
    country_profile: dict,
    language_profile: dict,
) -> dict:
    base_asr_languages = get_base_asr_languages(payload.country_code, region=None)
    return {
        "country_code": payload.country_code.upper(),
        "base_asr_languages": base_asr_languages,
        "target_language": payload.target_language.lower(),
        "bridge_language": payload.bridge_language.lower(),
        "script": payload.script.lower(),
        "dialect_label": payload.dialect_label,
        "teaching_mode": payload.teaching_mode,
        "allow_code_switching": payload.allow_code_switching,
        "consent_training_use": payload.consent_training_use,
        "drift_policy": country_profile.get("drift_policy"),
        "asr_strategy": country_profile.get("asr_strategy"),
        "language_profile": {
            "display_name": language_profile.get("display_name"),
            "native_name": language_profile.get("native_name"),
            "bridge_languages": language_profile.get("bridge_languages", []),
            "default_script": language_profile.get("default_script"),
        },
    }


def _normalize_reply_for_repeat_check(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _last_assistant_replies(message_history: list[dict], limit: int = 4) -> list[str]:
    replies: list[str] = []
    for message in reversed(message_history):
        if message.get("role") != "assistant":
            continue
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        replies.append(content)
        if len(replies) >= limit:
            break
    return replies


def _build_repeat_breaker_reply(
    hearing: hearing_svc.HearingResult,
    teacher_text: str,
    recent_assistant_replies: list[str],
) -> str:
    teacher_words = len((teacher_text or "").split())
    if hearing.mode == "english":
        candidates = (
            [
                "Okay. Can you say it once as a full sentence?",
                "Okay. Can you give one simple example?",
                "Okay. Can you say the same idea in easier words?",
            ]
            if teacher_words <= 4
            else [
                "Okay. Can you give one simple example?",
                "Okay. Can you say the same idea in easier words?",
                "Okay. Can you say it once as a full sentence?",
            ]
        )
    elif hearing.mode == "mixed":
        candidates = (
            [
                "ठिक छ। यो एकपटक पुरा वाक्यमा भन्न सक्छौ?",
                "ठिक छ। एउटा सजिलो उदाहरण दिन सक्छौ?",
                "ठिक छ। यही कुरा अझ सजिलो शब्दमा भन्न सक्छौ?",
            ]
            if teacher_words <= 4
            else [
                "ठिक छ। एउटा सजिलो उदाहरण दिन सक्छौ?",
                "ठिक छ। यही कुरा अझ सजिलो शब्दमा भन्न सक्छौ?",
                "ठिक छ। यो एकपटक पुरा वाक्यमा भन्न सक्छौ?",
            ]
        )
    else:
        candidates = (
            [
                "ठिक छ। यो एकपटक पुरा वाक्यमा भन्न सक्छौ?",
                "ठिक छ। एउटा सजिलो उदाहरण दिन सक्छौ?",
                "ठिक छ। यही कुरा अझ सजिलो शब्दमा भन्न सक्छौ?",
            ]
            if teacher_words <= 4
            else [
                "ठिक छ। एउटा सजिलो उदाहरण दिन सक्छौ?",
                "ठिक छ। यही कुरा अझ सजिलो शब्दमा भन्न सक्छौ?",
                "ठिक छ। यो एकपटक पुरा वाक्यमा भन्न सक्छौ?",
            ]
        )

    recent_normalized = {
        _normalize_reply_for_repeat_check(reply) for reply in recent_assistant_replies
    }
    for candidate in candidates:
        if _normalize_reply_for_repeat_check(candidate) not in recent_normalized:
            return candidate
    return candidates[0]


def _build_policy_reply(
    hearing: hearing_svc.HearingResult,
    behavior_policy: behavior_policy_svc.BehaviorPolicy,
    teacher_text: str,
) -> str:
    prompt_family = behavior_policy.prompt_family
    teach_language = behavior_policy.teach_language.upper() if behavior_policy.teach_language != "new" else "Newari"

    if hearing.mode == "english":
        if behavior_policy.turn_goal == "ACCEPT_AND_MOVE":
            if prompt_family == "ask_register_variant":
                return "Ohh okay. Is there a more casual way to say it too?"
            if prompt_family == "ask_example":
                return "Ohh okay. Can you use it in one simple example?"
            return "Ohh okay. So that means this is the better way, right?"
        if prompt_family == "ask_full_sentence":
            return "Wait, can you say it once as a full sentence?"
        if prompt_family == "ask_example":
            return "Ohh okay. Can you give one simple example?"
        if prompt_family == "ask_simple_rephrase":
            return "Wait, can you say the same thing in easier words?"
        if prompt_family == "ask_local_variant":
            return "Ohh okay. Is there a more local way to say that?"
        if prompt_family == "ask_target_language":
            return f"Ohh okay… how would you say that in {teach_language}?"
        if prompt_family == "confirm_meaning":
            return "Ohh okay… so that means what you said there, right?"
        return "Ohh okay… what's the natural way to say that?"

    if hearing.mode == "mixed":
        if behavior_policy.turn_goal == "ACCEPT_AND_MOVE":
            if prompt_family == "ask_register_variant":
                return "ओह ठीक छ। अलि casual तरिकाले पनि भन्छन्?"
            if prompt_family == "ask_example":
                return "ओह ठीक छ। एउटा सजिलो example दिन सक्छौ?"
            return "ओह ठीक छ। भनेपछि यही राम्रो तरिका हो, है?"
        if prompt_family == "ask_full_sentence":
            return "wait, यो एकपटक पुरा वाक्यमा भन्न सक्छौ?"
        if prompt_family == "ask_example":
            return "ओह ठीक छ। एउटा सजिलो example दिन सक्छौ?"
        if prompt_family == "ask_simple_rephrase":
            return "ओह ठीक छ। यही कुरा अझ सजिलो शब्दमा भन्न सक्छौ?"
        if prompt_family == "ask_local_variant":
            return "ओह ठीक छ। अलि local तरिकाले पनि भन्छन्?"
        if prompt_family == "ask_target_language":
            return f"ओह ठीक छ… यो {teach_language} मा कसरी भन्छन्?"
        if prompt_family == "confirm_meaning":
            return "ओह ठीक छ… भनेपछि त्यसको मतलब यही हो, है?"
        return "ओह ठीक छ… natural तरिकाले कसरी भन्छन्?"

    if behavior_policy.turn_goal == "ACCEPT_AND_MOVE":
        if prompt_family == "ask_register_variant":
            return "ओह ठीक छ। अलि casual तरिकाले पनि भन्छन्?"
        if prompt_family == "ask_example":
            return "ओह ठीक छ। एउटा सजिलो उदाहरण दिन सक्छौ?"
        return "ओह ठीक छ। भनेपछि यही राम्रो तरिका हो, है?"
    if prompt_family == "ask_full_sentence":
        return "पर्ख… यो एकपटक पुरा वाक्यमा भन्न सक्छौ?"
    if prompt_family == "ask_example":
        return "ओह ठीक छ। एउटा सजिलो उदाहरण दिन सक्छौ?"
    if prompt_family == "ask_simple_rephrase":
        return "ओह ठीक छ। यही कुरा अझ सजिलो शब्दमा भन्न सक्छौ?"
    if prompt_family == "ask_local_variant":
        return "ओह ठीक छ। अलि स्थानीय तरिकाले पनि भन्छन्?"
    if prompt_family == "ask_target_language":
        return f"ओह ठीक छ… यो {teach_language} मा कसरी भन्छन्?"
    if prompt_family == "confirm_meaning":
        return "ओह ठीक छ… भनेपछि त्यसको मतलब यही हो, है?"
    return "ओह ठीक छ… स्वाभाविक रूपमा कसरी भन्छन्?"

async def _load_message_history(session_id: str) -> list[dict]:
    raw = await cache.valkey.get(_MSG_HISTORY_KEY.format(session_id=session_id))
    return json.loads(raw) if raw else []


async def _save_message_history(session_id: str, messages: list[dict]) -> None:
    # Always preserve the system message at index 0; trim the rest
    system = [messages[0]] if messages and messages[0].get("role") == "system" else []
    rest = [m for m in messages if m.get("role") != "system"]
    trimmed = system + rest[-(_MAX_CONTEXT_TURNS * 2):]
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


def _build_cross_session_prompt_context(
    *,
    long_term_memory: memory_service_svc.StructuredSessionMemory,
    approved_rules: list,
) -> str:
    topics: list[str] = []
    if long_term_memory.active_topic:
        topics.append(long_term_memory.active_topic)
    topics.extend(long_term_memory.recent_taught_words[-5:])
    topics = list(dict.fromkeys(topic for topic in topics if topic))

    style_memory = long_term_memory.style_memory or {}
    register_hint = style_memory.get("register_estimate") or "unknown"
    speech_rate = style_memory.get("speech_rate") or "unknown"
    dialect_hint = style_memory.get("dialect_guess") or "unknown"
    approved_rule_lines = [f"- {rule.rule_text[:120]}" for rule in approved_rules[:3]]
    prior_corrections = long_term_memory.recent_corrections[-3:]

    return (
        "\n## Cross-session memory\n"
        f"- Previous taught words: {', '.join(long_term_memory.recent_taught_words[-6:]) if long_term_memory.recent_taught_words else 'none'}\n"
        f"- Recent corrections: {', '.join(prior_corrections) if prior_corrections else 'none'}\n"
        f"- Recent topics: {', '.join(topics) if topics else 'none'}\n"
        f"- Active language tendency: {long_term_memory.active_language or 'unknown'}\n"
        f"- Teacher register tendency: {register_hint}\n"
        f"- Teacher style memory: rate={speech_rate}, dialect={dialect_hint}, style={long_term_memory.user_style}\n"
        f"- Approved teachings: {'; '.join(approved_rule_lines) if approved_rule_lines else 'none'}\n"
        "Treat these as durable memory from earlier sessions with the same teacher.\n"
    )


# ─── REST: create session ────────────────────────────────────────────────────

@router.post("/api/sessions")
async def create_session(
    payload: SessionCreateRequest = Body(default_factory=SessionCreateRequest),
    user_id: str = Depends(get_current_user_flexible),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new teaching session row and return the session_id."""
    session_id = str(uuid.uuid4())
    profile = await _load_tone_profile(user_id)
    country_profile = load_country_profile(payload.country_code)
    if not validate_country_target_language(payload.country_code, payload.target_language):
        raise HTTPException(status_code=400, detail="unsupported_target_language_for_country")
    language_profile = load_language_profile(payload.target_language)
    if payload.teaching_mode not in _TEACHING_MODES:
        raise HTTPException(status_code=400, detail="unsupported_teaching_mode")
    allowed_scripts = {str(script).lower() for script in language_profile.get("scripts", [])}
    if payload.script.lower() not in allowed_scripts:
        raise HTTPException(status_code=400, detail="unsupported_script_for_language")
    if payload.bridge_language.lower() not in {str(item).lower() for item in language_profile.get("bridge_languages", [])}:
        raise HTTPException(status_code=400, detail="unsupported_bridge_language")
    session_contract = _build_session_language_contract(
        payload,
        country_profile=country_profile,
        language_profile=language_profile,
    )
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
        country_code=session_contract["country_code"],
        base_asr_languages=session_contract["base_asr_languages"],
        target_language=session_contract["target_language"],
        bridge_language=session_contract["bridge_language"],
        script=session_contract["script"],
        dialect_label=session_contract["dialect_label"],
        teaching_mode=session_contract["teaching_mode"],
        allow_code_switching=session_contract["allow_code_switching"],
        consent_training_use=session_contract["consent_training_use"],
        session_language_contract=session_contract,
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
        "session_language_contract": session_contract,
    }


@router.post("/api/sessions/{session_id}/messages/{message_id}/correction")
async def submit_teacher_correction(
    session_id: str,
    message_id: str,
    payload: CorrectionRequest,
    user_id: str = Depends(get_current_user_flexible),
    db: AsyncSession = Depends(get_db),
) -> dict:
    session = await db.get(TeachingSession, session_id)
    if session is None or session.teacher_id != user_id:
        raise HTTPException(status_code=404, detail="session_not_found")
    message = await db.get(Message, message_id)
    if message is None or message.session_id != session_id or message.role != "teacher":
        raise HTTPException(status_code=404, detail="message_not_found")

    contract = dict(session.session_language_contract or {})
    language_profile = load_language_profile(str(session.target_language or contract.get("target_language") or "ne"))
    action = payload.action.strip().lower()
    if action not in {"accept", "edit", "wrong_language", "skip"}:
        raise HTTPException(status_code=400, detail="unsupported_correction_action")

    corrected_text = payload.transcript.strip() if payload.transcript else None
    if action == "accept":
        corrected_text = message.text
    if action == "skip":
        await db.commit()
        return {"message_id": message.id, "status": "skipped"}

    drift_type = "wrong_target_language" if action == "wrong_language" else str(message.asr_drift_type or "no_drift")
    normalization = normalize_text_for_training(
        corrected_text or "",
        language_code=str(message.target_language or session.target_language or "ne"),
        script=str(message.script or session.script or "devanagari"),
        normalization_rules=get_normalization_rules(str(message.target_language or session.target_language or "ne")),
    )
    error = classify_asr_error(
        raw_stt=str(message.raw_stt or message.text or ""),
        teacher_correction=corrected_text or "",
        language_profile=language_profile,
        script=str(message.script or session.script or "devanagari"),
        drift_type=drift_type,
    )
    quality = assign_training_tier(
        audio_quality=float(message.audio_quality or 0.0),
        stt_confidence=float(message.stt_confidence or 0.0),
        teacher_verified=action != "skip",
        teacher_corrected=action in {"edit", "wrong_language"},
        consent_training_use=bool(session.consent_training_use),
        asr_drift_type=drift_type,
        error_type=error["error_type"],
        language_profile=language_profile,
    )
    await message_store.apply_teacher_correction(
        db,
        message=message,
        teacher_id=user_id,
        corrected_text=corrected_text,
        normalized_transcript=normalization.get("normalized_text"),
        asr_drift_type=drift_type,
        correction_error_type=error["error_type"],
        correction_error_family=error["error_family"],
        training_tier=quality["training_tier"],
        training_eligible=quality["training_eligible"],
        consent_training_use=bool(session.consent_training_use),
        source_type="manual_teacher" if action in {"accept", "edit"} else "wrong_language",
        meaning_nepali=payload.meaning_nepali,
        meaning_english=payload.meaning_english,
        correction_metadata={
            "action": action,
            "reason": quality["reason"],
            "base_asr_languages": contract.get("base_asr_languages", []),
            "normalization_warnings": normalization.get("warnings", []),
        },
    )
    await db.commit()
    return {
        "message_id": message.id,
        "teacher_verified": message.teacher_verified,
        "training_tier": message.training_tier,
        "training_eligible": message.training_eligible,
        "correction_error_type": message.correction_error_type,
        "asr_drift_type": message.asr_drift_type,
    }


# ─── WebSocket endpoint ───────────────────────────────────────────────────────

@router.websocket("/ws/session/{session_id}")
async def conversation_ws(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Depends(get_ws_user),
):
    origin = websocket.headers.get("origin")
    allowed = [u.strip() for u in settings.app_url.split(",")]
    if origin and not any(origin.startswith(a) for a in allowed) and not any("localhost" in a for a in allowed):
        logger.warning(f"WS origin rejected: {origin}")
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info("WS connected session=%s user=%s", session_id, user_id)

    profile = await _load_tone_profile(user_id)

    # Cross-session memory: hydrate previous_topics + carry approved rules so LIPI
    # behaves as if it remembers what this teacher has already taught.
    approved_rules: list = []
    async with SessionLocal() as hydrate_db:
        long_term = await memory_service_svc.load_teacher_long_term_memory(
            hydrate_db, teacher_id=user_id
        )
        approved_rules = await correction_graph_svc.load_approved_rules_for_teacher(
            hydrate_db,
            teacher_id=user_id,
            language_key=long_term.active_language,
        )
    if long_term.recent_taught_words:
        profile.previous_topics = list(long_term.recent_taught_words)[-6:]
    if long_term.active_topic:
        profile.preferred_topics = list(dict.fromkeys([long_term.active_topic, *profile.preferred_topics]))[:6]
    remembered_register = str((long_term.style_memory or {}).get("register_estimate") or "").strip().lower()
    if remembered_register in {"hajur", "tapai", "timi", "ta"}:
        profile.register = remembered_register
    cross_session_prompt_context = _build_cross_session_prompt_context(
        long_term_memory=long_term,
        approved_rules=approved_rules,
    )

    message_history: list[dict] = await _load_message_history(session_id)
    user: User | None = None
    curriculum_profile: UserCurriculumProfile | None = None
    session_contract: dict | None = None

    http = websocket.app.state.http

    # Ensure session row exists
    async with SessionLocal() as db:
        session = await db.get(TeachingSession, session_id)
        if not session:
            db.add(TeachingSession(
                id=session_id,
                teacher_id=user_id,
                register_used=profile.register,
            ))
            session_contract = {
                "country_code": "NP",
                "base_asr_languages": ["ne", "en"],
                "target_language": "ne",
                "bridge_language": "ne",
                "script": "devanagari",
                "dialect_label": None,
                "teaching_mode": "free_conversation",
                "allow_code_switching": True,
                "consent_training_use": False,
                "drift_policy": "prefer_teacher_selected_language_over_auto_detect",
            }
        else:
            session_contract = dict(session.session_language_contract or {})
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

    session_contract = session_contract or {
        "country_code": "NP",
        "base_asr_languages": ["ne", "en"],
        "target_language": "ne",
        "bridge_language": "ne",
        "script": "devanagari",
        "dialect_label": None,
        "teaching_mode": "free_conversation",
        "allow_code_switching": True,
        "consent_training_use": False,
        "drift_policy": "prefer_teacher_selected_language_over_auto_detect",
    }
    try:
        target_language_profile = load_language_profile(session_contract.get("target_language", "ne"))
        profile.native_language = str(target_language_profile.get("display_name") or session_contract.get("target_language"))
        profile.other_languages = list(
            dict.fromkeys(
                [profile.native_language, *session_contract.get("base_asr_languages", []), session_contract.get("bridge_language", "")]
            )
        )
    except ValueError:
        target_language_profile = {"display_name": session_contract.get("target_language", "ne")}
        profile.native_language = str(session_contract.get("target_language", "ne"))

    # Determine if teach mode is enabled (check early for system prompt)
    disable_teach_behaviors = os.getenv("LIPI_DISABLE_TEACH_BEHAVIORS", "").lower() == "true"
    teach_mode_enabled = not disable_teach_behaviors

    # Build system prompt based on mode
    if teach_mode_enabled:
        system_prompt = build_system_prompt(profile, session_contract=session_contract) + cross_session_prompt_context
    else:
        system_prompt = (
            "You are a warm, helpful, and friendly conversational AI. "
            "Engage naturally with the user on any topic they bring up. "
            "Be concise, genuine, and interested in what they say. "
            "Ask follow-up questions when it helps the conversation flow. "
            "Don't have hidden agendas or try to extract information—just be a good conversational partner."
        )

    if not message_history or message_history[0].get("role") != "system":
        message_history.insert(0, {"role": "system", "content": system_prompt})

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
            session_turn_memory = await topic_memory_svc.load_session_memory(session_id)
            async with SessionLocal() as keyterm_db:
                turn_keyterms = await keyterm_service_svc.prepare_turn_keyterms(
                    keyterm_db,
                    teacher_id=user_id,
                    session_memory=session_turn_memory,
                    long_term_memory=long_term,
                    target_language=profile.native_language,
                )

            stt_t0 = time.monotonic()
            stt_result = await stt_svc.transcribe(
                audio_bytes,
                http,
                prompt=turn_keyterms.prompt_hint,
                language_hint=long_term.active_language or session_turn_memory.get("active_language") or None,
                session_language_contract=session_contract,
                teacher_id=user_id,
                session_id=session_id,
            )
            stt_ms = int((time.monotonic() - stt_t0) * 1000)

            hearing = hearing_svc.analyze_hearing(stt_result)
            repair_result = transcript_repair_svc.repair_transcript(
                transcript=hearing.clean_text,
                stt_confidence=hearing.confidence,
                keyterms=turn_keyterms,
            )
            teacher_text: str = repair_result.repaired_text.strip() or hearing.clean_text
            if not teacher_text:
                await websocket.send_json({"type": "empty_audio"})
                continue
            effective_confidence = max(hearing.confidence, repair_result.confidence_after)
            hearing = replace(
                hearing,
                clean_text=teacher_text,
                confidence=effective_confidence,
                audio_quality_score=max(hearing.audio_quality_score, min(effective_confidence, 0.99)),
            )
            normalization = normalize_text_for_training(
                teacher_text,
                language_code=str(session_contract.get("target_language") or "ne"),
                script=str(session_contract.get("script") or "devanagari"),
                normalization_rules=get_normalization_rules(str(session_contract.get("target_language") or "ne")),
            )
            initial_quality = assign_training_tier(
                audio_quality=float(hearing.audio_quality_score or 0.0),
                stt_confidence=float(hearing.confidence or 0.0),
                teacher_verified=False,
                teacher_corrected=False,
                consent_training_use=bool(session_contract.get("consent_training_use", False)),
                asr_drift_type=str(stt_result.get("asr_drift_type") or "no_drift"),
                error_type=None,
                language_profile=target_language_profile,
            )

            await websocket.send_json({
                "type": "transcript",
                "text": teacher_text,
                "language": hearing.language,
                "confidence": hearing.confidence,
                "mode": hearing.mode,
                "quality": hearing.quality_label,
                "repair_applied": bool(repair_result.applied_repairs),
                "selected_language": stt_result.get("selected_language"),
                "detected_language": stt_result.get("detected_language"),
                "target_language": stt_result.get("target_language"),
                "base_asr_languages": stt_result.get("base_asr_languages"),
                "needs_teacher_confirmation": stt_result.get("needs_teacher_confirmation", False),
                "asr_drift_type": stt_result.get("asr_drift_type"),
                "code_switch_ratio": stt_result.get("code_switch_ratio", 0.0),
                "candidates": stt_result.get("candidates", []),
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
                if teach_mode_enabled:
                    system_prompt = build_system_prompt(profile) + cross_session_prompt_context
                    message_history[0] = {"role": "system", "content": system_prompt}
                logger.info("Register switched to %s", new_register)

            # ── 3.5 Audio Understanding Sidecar ───────────────────────────
            # Short timeout allows graceful fallback without killing the WS loop
            audio_signals = await audio_understanding_svc.extract_audio_signals(
                http=http,
                audio_bytes=audio_bytes,
                rough_transcript=teacher_text,
            )

            # ── 4. LLM (stream tokens to client) ─────────────────────────
            memory = session_turn_memory
            memory["latest_teacher_text"] = teacher_text
            interpretation = turn_interpreter_svc.interpret_turn(hearing, memory)
            turn_intelligence = turn_intelligence_svc.analyze_turn(
                hearing=hearing,
                repaired_transcript=repair_result,
                keyterms=turn_keyterms,
                memory_context=memory,
            )
            if turn_intelligence.intent.label == "register_instruction":
                requested_register = next(
                    (
                        str(entity.attributes.get("register") or "").strip().lower()
                        for entity in turn_intelligence.entities
                        if entity.entity_type == "honorific_or_register_term"
                    ),
                    "",
                )
                if requested_register in {"hajur", "tapai", "timi", "ta"} and requested_register != profile.register:
                    profile.register = requested_register
                    if teach_mode_enabled:
                        system_prompt = build_system_prompt(profile) + cross_session_prompt_context
                        message_history[0] = {"role": "system", "content": system_prompt}
                    logger.info("Register adjusted from turn intelligence to %s", requested_register)
            understanding = input_understanding_svc.merge_signals(
                turn_id=str(uuid.uuid4()),
                hearing=hearing,
                interpretation=interpretation,
                audio_signals=audio_signals,
                intent_label=turn_intelligence.intent.label,
                intent_confidence=turn_intelligence.intent.confidence,
                secondary_intents=turn_intelligence.intent.secondary_labels,
                usable_for_learning=turn_intelligence.quality.usable_for_learning,
                unusable_reason=turn_intelligence.quality.reason_if_not,
                learning_weight=turn_intelligence.learning_weight,
                memory_context=memory
            )
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
            recent_assistant_replies = _last_assistant_replies(message_history, limit=4)
            if not teach_mode_enabled and turn_index == 2:
                logger.info("⚠️  TEACH MODE DISABLED — Running in regular LLM mode (testing)")
            behavior_policy = behavior_policy_svc.choose_behavior_policy(
                teacher_model=teacher_model,
                session_memory=structured_memory,
                correction_count_recent=correction_summary.recent_count,
                understanding=understanding,
                target_language=profile.native_language,
                recent_assistant_replies=recent_assistant_replies,
                teach_mode_enabled=teach_mode_enabled,
            )
            routing_hooks = routing_hooks_svc.build_routing_hooks(
                teacher_model=teacher_model,
                understanding=understanding,
                behavior_policy=behavior_policy,
            )
            clarification_only = (
                not hearing.conversation_allowed
                or turn_intelligence.intent.label == "low_signal"
                or (
                    hearing.quality_label == "medium"
                    and hearing.confidence < 0.64
                    and turn_intelligence.intent.label in {"unknown", "confirmation", "clarification"}
                )
            )
            llm_ms = 0
            if clarification_only and teach_mode_enabled:
                lipi_text = _build_policy_reply(hearing, behavior_policy, teacher_text)
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
                    approved_rules=approved_rules,
                    turn_intelligence=turn_intelligence,
                )
                turn_guidance = response_package.turn_guidance + (
                    "## Routing hooks\n"
                    f"- Dialect adapter: {routing_hooks.dialect_adapter or 'none'}\n"
                    f"- Behavior adapter: {routing_hooks.behavior_adapter or 'none'}\n"
                    f"- STT bias: {routing_hooks.stt_bias or 'none'}\n"
                    f"- TTS voice profile: {routing_hooks.tts_voice_profile or 'none'}\n"
                    f"- Response ranker: {routing_hooks.response_ranker or 'none'}\n"
                )

                # In regular LLM mode, use simple guidance without teach-specific instructions
                if not teach_mode_enabled:
                    turn_guidance = (
                        "You are a helpful, friendly conversational AI assistant. "
                        "Have natural conversations on any topic the user brings up. "
                        "Be concise, warm, and engage naturally with what they say. "
                        "Ask questions when appropriate, but don't force it. "
                        "No structured learning goals or language extraction—just be a good conversational partner."
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
            # In regular LLM mode, skip teach-mode-specific guards
            if teach_mode_enabled:
                guard_result = post_generation_guard_svc.guard_response(
                    lipi_text,
                    hearing=hearing,
                    understanding=understanding,
                    policy=behavior_policy,
                )
                lipi_text = response_cleanup_svc.finalize_reply(guard_result.text, hearing)
                normalized_reply = _normalize_reply_for_repeat_check(lipi_text)
                if normalized_reply and any(
                    normalized_reply == _normalize_reply_for_repeat_check(previous)
                    for previous in recent_assistant_replies
                ):
                    lipi_text = _build_repeat_breaker_reply(
                        hearing,
                        teacher_text,
                        recent_assistant_replies,
                    )
            else:
                # Regular LLM mode: minimal cleanup only
                lipi_text = response_cleanup_svc.finalize_reply(lipi_text, hearing)
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
                    turn_intelligence=turn_intelligence,
                )
                teacher_message = await message_store.persist_teacher_turn(
                    db,
                    session_id=session_id,
                    user_id=user_id,
                    turn_index=current_turn,
                    text=teacher_text,
                    country_code=session_contract.get("country_code"),
                    target_language=session_contract.get("target_language"),
                    bridge_language=session_contract.get("bridge_language"),
                    script=session_contract.get("script"),
                    dialect_label=session_contract.get("dialect_label"),
                    detected_language=hearing.language,
                    selected_language=stt_result.get("selected_language"),
                    code_switch_ratio=stt_result.get("code_switch_ratio"),
                    asr_drift_type=stt_result.get("asr_drift_type"),
                    needs_teacher_confirmation=bool(stt_result.get("needs_teacher_confirmation", False)),
                    audio_quality=hearing.audio_quality_score,
                    audio_path=audio_path,
                    stt_confidence=hearing.confidence,
                    teacher_verified=False,
                    audio_duration_ms=stt_result.get("duration_ms"),
                    raw_stt=stt_result.get("selected_transcript") or teacher_text,
                    base_candidate_transcript=next((c.get("transcript") for c in stt_result.get("candidates", []) if c.get("candidate_type") == "base_nepali"), None),
                    english_candidate_transcript=next((c.get("transcript") for c in stt_result.get("candidates", []) if c.get("candidate_type") == "base_english"), None),
                    target_candidate_transcript=next((c.get("transcript") for c in stt_result.get("candidates", []) if c.get("candidate_type") == "target_adapter"), None),
                    acoustic_transcript=stt_result.get("selected_transcript") or teacher_text,
                    normalized_transcript=normalization.get("normalized_text"),
                    training_tier=initial_quality["training_tier"],
                    training_eligible=initial_quality["training_eligible"],
                    consent_training_use=bool(session_contract.get("consent_training_use", False)),
                    candidates=stt_result.get("candidates", []),
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
                        "session_language_contract": session_contract,
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
                await turn_intelligence_svc.persist_turn_intelligence(
                    db,
                    message_id=teacher_message.id,
                    session_id=session_id,
                    teacher_id=user_id,
                    transcript_original=repair_result.original_text,
                    transcript_final=teacher_text,
                    intelligence=turn_intelligence,
                )
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
                updated_structured_memory = await memory_service_svc.update_session_memory(
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
                long_term = updated_structured_memory
                await websocket.send_json(
                    {
                        "type": "turn_saved",
                        "message_id": teacher_message.id,
                        "session_id": session_id,
                        "needs_teacher_confirmation": bool(teacher_message.needs_teacher_confirmation),
                        "training_tier": teacher_message.training_tier,
                        "asr_drift_type": teacher_message.asr_drift_type,
                    }
                )

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
                teacher_message_id=teacher_message.id,
                turn_intelligence=turn_intelligence.to_dict(),
                audio_path=audio_path,
                target_language=str(session_contract.get("target_language") or ""),
                session_language_contract=session_contract,
                normalized_transcript=normalization.get("normalized_text"),
                training_tier=initial_quality["training_tier"],
                asr_drift_type=str(stt_result.get("asr_drift_type") or "no_drift"),
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
