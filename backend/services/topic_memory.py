"""Lightweight session memory for continuity, personality, and follow-up quality."""

from __future__ import annotations

import json
import re
from collections import Counter

from cache import valkey

_MEMORY_KEY = "session:{session_id}:topic_memory"
_MEMORY_TTL_SECONDS = 3600
_MAX_TOPICS = 5
_MAX_WORDS = 6
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]+")
_LATIN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_NEWARI_HINTS = (
    "newari",
    "nepal bhasa",
    "नेवारी",
    "नेपाल भाषा",
)
_LOCAL_LANGUAGE_HINTS = (
    "maithili",
    "bhojpuri",
    "tharu",
    "tamang",
    "sherpa",
    "gurung",
    "rai",
    "limbu",
    "नेवारी",
    "मैथिली",
    "भोजपुरी",
    "थारु",
    "तामाङ",
)
_STOPWORDS = {
    "the", "and", "you", "your", "are", "for", "that", "this", "with", "have",
    "was", "were", "from", "they", "them", "what", "when", "where", "how",
    "का", "को", "की", "मा", "छ", "छु", "हो", "र", "त", "यो", "त्यो", "एक",
    "म", "तिमी", "तपाईं", "हजुर", "मलाई", "होइन", "भनेर", "अनि", "के", "कस्तो",
}
_CASUAL_STYLE_HINTS = (
    "buddy",
    "bro",
    "dude",
    "haha",
    "lol",
    "साथी",
    "यार",
    "तिमी",
    "तँ",
)
_FORMAL_STYLE_HINTS = (
    "hajur",
    "sir",
    "madam",
    "please",
    "धन्यवाद",
    "कृपया",
    "तपाईं",
    "हजुर",
)
_CORRECTION_HINTS = (
    "होइन",
    "यसरी भनिन्छ",
    "यसरी भन्नु",
    "correct is",
    "say it like",
    "not like that",
)


def _extract_terms(text: str) -> list[str]:
    tokens = [token.lower() for token in _LATIN_RE.findall(text)]
    tokens.extend(_DEVANAGARI_RE.findall(text))
    filtered: list[str] = []
    for token in tokens:
        stripped = token.strip().lower()
        if len(stripped) < 2 or stripped in _STOPWORDS:
            continue
        filtered.append(stripped)
    return filtered


def _infer_language_hint(text: str, detected_language: str | None) -> str | None:
    lowered = text.lower()
    if any(hint in lowered for hint in _NEWARI_HINTS):
        return "newari"
    if any(hint in lowered for hint in _LOCAL_LANGUAGE_HINTS):
        return "local_language"
    if detected_language:
        return detected_language.lower()
    return None


def _extract_taught_words(text: str) -> list[str]:
    words: list[str] = []
    for token in _extract_terms(text):
        if len(token) <= 24 and token not in words:
            words.append(token)
        if len(words) >= _MAX_WORDS:
            break
    return words


async def load_session_memory(session_id: str) -> dict:
    raw = await valkey.get(_MEMORY_KEY.format(session_id=session_id))
    if not raw:
        return _empty_memory()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _empty_memory()


def _empty_memory() -> dict:
    return {
        "active_language": None,
        "recent_topics": [],
        "taught_words": [],
        "last_taught_word": None,
        "teacher_intent": None,
        "last_correction": None,
        "user_style": "neutral",
        "last_lipi_question": None,
        "last_lipi_reply": None,
    }


def _infer_user_style(text: str) -> str:
    lowered = text.lower()
    if any(hint in lowered for hint in _FORMAL_STYLE_HINTS):
        return "formal"
    if any(hint in lowered for hint in _CASUAL_STYLE_HINTS):
        return "casual"
    return "neutral"


def _extract_last_correction(text: str) -> str | None:
    lowered = text.lower()
    if not any(hint in lowered for hint in _CORRECTION_HINTS):
        return None
    trimmed = " ".join(text.strip().split())
    return trimmed[:100] if trimmed else None


async def update_session_memory(
    session_id: str,
    *,
    teacher_text: str,
    lipi_text: str,
    detected_language: str | None,
    last_question: str | None = None,
) -> dict:
    memory = await load_session_memory(session_id)

    term_counter = Counter(memory.get("recent_topics", []))
    for token in _extract_terms(f"{teacher_text} {lipi_text}"):
        term_counter[token] += 1

    recent_topics = [token for token, _ in term_counter.most_common(_MAX_TOPICS)]
    taught_words = list(dict.fromkeys(memory.get("taught_words", []) + _extract_taught_words(teacher_text)))[-_MAX_WORDS:]

    lowered = teacher_text.lower()
    if "how do you say" in lowered or "भन्ने" in teacher_text or "means" in lowered:
        teacher_intent = "teaching_word"
    elif "story" in lowered or "कथा" in teacher_text:
        teacher_intent = "story"
    elif "feel" in lowered or "लाग्छ" in teacher_text or "खुसी" in teacher_text:
        teacher_intent = "feeling"
    else:
        teacher_intent = memory.get("teacher_intent")

    taught_tail = taught_words[-1] if taught_words else memory.get("last_taught_word")

    updated = {
        "active_language": _infer_language_hint(teacher_text, detected_language) or memory.get("active_language"),
        "recent_topics": recent_topics,
        "taught_words": taught_words,
        "last_taught_word": taught_tail,
        "teacher_intent": teacher_intent,
        "last_correction": _extract_last_correction(teacher_text) or memory.get("last_correction"),
        "user_style": _infer_user_style(teacher_text) if teacher_text.strip() else memory.get("user_style", "neutral"),
        "last_lipi_question": last_question or memory.get("last_lipi_question"),
        "last_lipi_reply": lipi_text[:140] if lipi_text else memory.get("last_lipi_reply"),
    }

    await valkey.setex(
        _MEMORY_KEY.format(session_id=session_id),
        _MEMORY_TTL_SECONDS,
        json.dumps(updated),
    )
    return updated


def build_memory_block(memory: dict) -> str:
    topics = memory.get("recent_topics") or []
    taught_words = memory.get("taught_words") or []
    active_language = memory.get("active_language") or "unknown"
    teacher_intent = memory.get("teacher_intent") or "unknown"
    last_taught_word = memory.get("last_taught_word") or "none yet"
    last_correction = memory.get("last_correction") or "none yet"
    user_style = memory.get("user_style") or "neutral"
    last_lipi_question = memory.get("last_lipi_question") or "none yet"

    topic_line = ", ".join(topics) if topics else "none yet"
    taught_line = ", ".join(taught_words) if taught_words else "none yet"

    return f"""## Session memory
- Active language right now: {active_language}
- Current topic hints: {topic_line}
- Recently taught words: {taught_line}
- Last taught word: {last_taught_word}
- Teacher intent: {teacher_intent}
- User speaking style: {user_style}
- Last correction: {last_correction}
- Last question LIPI asked: {last_lipi_question}
- Use this memory to continue the thread naturally instead of restarting the lesson
"""
