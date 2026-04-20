"""
LLM service — vLLM primary, Groq fallback (circuit breaker pattern).
Never call Groq directly; it only fires when local vLLM fails.
"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import settings

logger = logging.getLogger("lipi.backend.llm")

_DEFAULT_MAX_TOKENS = 96
_DEFAULT_TEMPERATURE = 0.3

_HINDI_MARKERS = {
    "कैसे", "क्या", "है", "हूँ", "हैं", "नहीं", "लेकिन", "अगर", "क्यों",
    "मेरा", "मेरी", "आपका", "आपकी", "चलिए", "कहां", "अच्छा", "धन्यवाद",
    "चर्चा", "जारी", "रखना", "चाहते", "करते", "सकते",
}
_URDU_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_DEVANAGARI_WORD_RE = re.compile(r"[\u0900-\u097F]+")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_PAREN_RE = re.compile(r"\([^)]*\)")
_MULTISPACE_RE = re.compile(r"\s+")
_REPEATED_WORD_RE = re.compile(r"\b([A-Za-z]+)\s+\1\b", re.IGNORECASE)
_REPEATED_DEVANAGARI_RE = re.compile(r"([\u0900-\u097F]+)\s+\1")
_REPETITIVE_CLOSERS = {
    "तिमीलाई कस्तो छ?",
    "तिमीलाई के-के कुरा सिक्न मन छ?",
    "तिमीले भन्न खोजेको के हो?",
}
_EMOJI_MARKERS = ("😊", "😄", "😁", "🙂", "🤔", "✨")
_LESSON_META_PATTERNS = (
    "तिमीले यी शब्दहरू सिकाइरहेका छौ",
    "तिमी नेपाली भाषा सिक्दै छौ",
    "मलाई तिमी भनेर सम्बोधन गर्छौ",
    "तिमी के भन्न खोज्दै छौ",
)
_GENERIC_FILLER_PATTERNS = (
    "Teach me more",
    "teach me more",
    "Can you explain further",
    "Tell me more about this in detail",
    "मलाई अझ धेरै सिकाऊ",
    "अझै सिकाउनुस्",
)
_ROBOTIC_PHRASES = (
    "I will learn from you",
    "I am learning from you",
    "That is very interesting",
    "म तिमीले सिकाएको",
    "म सिक्दै छु",
    "यो निकै रोचक छ",
    "तपाईंले सिकाउनुभएको",
)
_FORMAL_TO_SPOKEN = (
    ("कृपया", ""),
    ("हुन्छ ?", "हुन्छ?"),
    ("हो र?", "हो?"),
)
_GENERIC_QUESTION_ENDINGS = (
    "teach me more",
    "tell me more",
    "explain more",
    "what else",
    "के अरू",
    "अझै",
)


def _tokenize_script_words(text: str, pattern: re.Pattern[str]) -> list[str]:
    return pattern.findall(text)


def _response_mode(teacher_text: str, detected_language: str | None) -> str:
    language = (detected_language or "").lower()
    devanagari_words = _tokenize_script_words(teacher_text, _DEVANAGARI_WORD_RE)
    latin_words = _tokenize_script_words(teacher_text, _LATIN_WORD_RE)

    if language == "en" or len(latin_words) > max(6, len(devanagari_words) * 2):
        return "english"
    if latin_words and devanagari_words:
        return "mixed"
    return "nepali"


def _score_language_purity(text: str) -> tuple[bool, str]:
    stripped = text.strip()
    if not stripped:
        return False, "empty"

    if _URDU_ARABIC_RE.search(stripped):
        return False, "urdu_script"

    devanagari_words = _tokenize_script_words(stripped, _DEVANAGARI_WORD_RE)
    latin_words = [w.lower() for w in _tokenize_script_words(stripped, _LATIN_WORD_RE)]
    hindi_hits = [w for w in devanagari_words if w in _HINDI_MARKERS]

    if len(hindi_hits) >= 2:
        return False, f"hindi_markers={','.join(hindi_hits[:4])}"

    # Teacher can switch to English, but mixed English-heavy answers should not
    # dominate when we're supposed to stay in Nepali.
    if latin_words and len(latin_words) > max(4, len(devanagari_words)):
        return False, "too_much_latin"

    return True, "ok"


# ─── vLLM (primary) ─────────────────────────────────────────────────────────

async def _vllm_stream(
    messages: list[dict],
    http: httpx.AsyncClient,
) -> AsyncIterator[str]:
    """Stream token deltas from local vLLM (OpenAI-compatible SSE)."""
    payload = {
        "model": settings.vllm_model,
        "messages": messages,
        "stream": True,
        "max_tokens": _DEFAULT_MAX_TOKENS,
        "temperature": _DEFAULT_TEMPERATURE,
    }
    async with http.stream(
        "POST",
        f"{settings.vllm_url}/v1/chat/completions",
        json=payload,
        timeout=settings.vllm_timeout,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                yield delta


async def _vllm_complete(
    messages: list[dict],
    http: httpx.AsyncClient,
) -> str:
    """Non-streaming vLLM completion."""
    resp = await http.post(
        f"{settings.vllm_url}/v1/chat/completions",
        json={
            "model": settings.vllm_model,
            "messages": messages,
            "stream": False,
            "max_tokens": _DEFAULT_MAX_TOKENS,
            "temperature": _DEFAULT_TEMPERATURE,
        },
        timeout=settings.vllm_timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _postprocess_teacher_reply(text: str) -> str:
    cleaned = _PAREN_RE.sub(" ", text)
    for marker in _EMOJI_MARKERS:
        cleaned = cleaned.replace(marker, " ")
    for marker in _GENERIC_FILLER_PATTERNS:
        cleaned = cleaned.replace(marker, " ")
    for phrase in _ROBOTIC_PHRASES:
        cleaned = cleaned.replace(phrase, " ")
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    cleaned = _MULTISPACE_RE.sub(" ", cleaned).strip()
    cleaned = _REPEATED_WORD_RE.sub(r"\1", cleaned)
    cleaned = _REPEATED_DEVANAGARI_RE.sub(r"\1", cleaned)

    if not cleaned:
        return ""

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[।!?])\s+", cleaned)
        if sentence.strip()
    ]

    if len(sentences) > 1 and sentences[-1] in _REPETITIVE_CLOSERS:
        sentences = sentences[:-1]

    if len(sentences) > 2:
        sentences = sentences[:2]

    cleaned = " ".join(sentences).strip()

    for pattern in _LESSON_META_PATTERNS:
        if pattern in cleaned and len(sentences) > 1:
            cleaned = cleaned.replace(pattern, "").strip(" ,।")
            cleaned = _MULTISPACE_RE.sub(" ", cleaned).strip()

    if cleaned.count("?") > 1:
        first = cleaned.find("?")
        cleaned = cleaned[: first + 1] + cleaned[first + 1 :].replace("?", "")
    if cleaned.count("？") > 1:
        first = cleaned.find("？")
        cleaned = cleaned[: first + 1] + cleaned[first + 1 :].replace("？", "")

    for from_text, to_text in _FORMAL_TO_SPOKEN:
        cleaned = cleaned.replace(from_text, to_text)

    cleaned = _strip_generic_questions(cleaned)
    cleaned = _normalize_spoken_pacing(cleaned)

    if len(cleaned) > 140:
        cleaned = cleaned[:140].rsplit(" ", 1)[0].rstrip(" ,;:-") + "।"

    return cleaned


def _strip_generic_questions(text: str) -> str:
    stripped = text.strip()
    lowered = stripped.lower()
    if not stripped:
        return stripped
    if any(lowered.endswith(ending) for ending in _GENERIC_QUESTION_ENDINGS):
        pieces = re.split(r"(?<=[।!?])\s+", stripped)
        stripped = pieces[0].strip() if pieces else stripped
    return stripped


def _normalize_spoken_pacing(text: str) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[।!?])\s+", text) if part.strip()]
    clipped: list[str] = []
    for part in parts[:2]:
        words = part.split()
        if len(words) > 14:
            part = " ".join(words[:14]).rstrip(",;:-")
            if not part.endswith(("।", "?", "!")):
                part += "।"
        clipped.append(part)
    normalized = " ".join(clipped).strip()
    normalized = _MULTISPACE_RE.sub(" ", normalized).strip()
    return normalized


async def _rewrite_to_pure_nepali(
    text: str,
    http: httpx.AsyncClient,
) -> str:
    rewrite_messages = [
        {
            "role": "system",
            "content": (
                "You are a Nepali text normalizer. Rewrite the assistant reply into "
                "clean, natural standard Nepali only. Keep the meaning. "
                "Do not use Hindi, Urdu script, or mixed-language phrasing. "
                "Return only the rewritten Nepali reply."
            ),
        },
        {"role": "user", "content": text},
    ]
    rewritten = await _vllm_complete(rewrite_messages, http)
    return rewritten.strip()


async def enforce_pure_nepali_reply(
    text: str,
    http: httpx.AsyncClient,
) -> str:
    normalized = _postprocess_teacher_reply(text)
    valid, reason = _score_language_purity(normalized)
    if valid:
        return normalized

    logger.warning("LLM reply failed Nepali purity check (%s): %r", reason, text[:200])

    try:
        rewritten = await _rewrite_to_pure_nepali(text, http)
        rewritten = _postprocess_teacher_reply(rewritten)
        valid, rewrite_reason = _score_language_purity(rewritten)
        if valid:
            logger.info("LLM reply rewritten into clean Nepali")
            return rewritten
        logger.warning(
            "Rewritten Nepali reply still failed purity check (%s): %r",
            rewrite_reason,
            rewritten[:200],
        )
    except Exception as exc:
        logger.warning("Nepali rewrite step failed: %s", exc)

    return "माफ गर्नुहोस्, फेरि छोटो गरी भन्नुहोस्।"


def _postprocess_multilingual_reply(text: str) -> str:
    cleaned = _postprocess_teacher_reply(text)
    if not cleaned:
        return "Sorry, please say that once more."
    return cleaned


def build_low_confidence_reply(mode: str) -> str:
    if mode == "english":
        return "I didn't quite catch that. Can you say it once more?"
    if mode == "mixed":
        return "म अलि बुझिनँ. Can you say that once more?"
    return "म अलि बुझिनँ। फेरि भन्न सक्छौ?"


def build_medium_confidence_reply(teacher_text: str, mode: str) -> str:
    snippet = " ".join(teacher_text.strip().split()[:7]).strip(" ,")
    if mode == "english":
        if snippet:
            return f"It sounds like you meant '{snippet}'. Is that right?"
        return "It sounds like I only caught part of that. Is that right?"
    if mode == "mixed":
        if snippet:
            return f"तिमीले '{snippet}' भन्न खोज्यौ जस्तो लाग्यो. Right?"
        return "तिमीले के भन्न खोज्यौ जस्तो लाग्यो. Right?"
    if snippet:
        return f"तिमीले '{snippet}' भन्न खोज्यौ जस्तो लाग्यो, है?"
    return "तिमीले के भन्न खोज्यौ जस्तो लाग्यो, है?"


# ─── Groq fallback ───────────────────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    reraise=True,
)
async def _groq_complete(
    messages: list[dict],
    http: httpx.AsyncClient,
) -> str:
    """Groq fallback — fires ONLY when local vLLM fails."""
    if not settings.groq_api_key:
        raise RuntimeError("Groq API key not configured — no fallback available")

    logger.warning("vLLM unavailable — routing to Groq fallback")

    resp = await http.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": _DEFAULT_MAX_TOKENS,
            "temperature": _DEFAULT_TEMPERATURE,
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ─── Public interface ────────────────────────────────────────────────────────

async def generate(
    messages: list[dict],
    http: httpx.AsyncClient,
    *,
    stream: bool = False,
) -> str | AsyncIterator[str]:
    """
    Generate a response from vLLM with automatic Groq fallback.

    Pass stream=True to get an async iterator of token deltas (vLLM only;
    fallback always returns a complete string).
    """
    try:
        if stream:
            # Caller gets the iterator; exceptions surface during iteration.
            # Wrap in a guarded generator so fallback still works.
            return _guarded_stream(messages, http)
        return await _vllm_complete(messages, http)
    except Exception as exc:
        if not settings.groq_api_key:
            logger.error("vLLM error with no Groq fallback configured: %s", exc)
            raise
        logger.warning("vLLM error (%s), activating Groq fallback", exc)
        return await _groq_complete(messages, http)


async def _guarded_stream(
    messages: list[dict],
    http: httpx.AsyncClient,
) -> AsyncIterator[str]:
    """Stream from vLLM; on any error fall back to a single Groq chunk."""
    try:
        async for token in _vllm_stream(messages, http):
            yield token
    except Exception as exc:
        if not settings.groq_api_key:
            logger.error("vLLM stream error with no Groq fallback configured: %s", exc)
            raise
        logger.warning("vLLM stream error (%s), falling back to Groq", exc)
        text = await _groq_complete(messages, http)
        yield text


async def generate_teacher_reply(
    messages: list[dict],
    http: httpx.AsyncClient,
    *,
    teacher_text: str,
    detected_language: str | None = None,
) -> str:
    """Generate a teacher-facing reply and enforce Nepali purity before use."""
    raw = await generate(messages, http, stream=False)
    if not isinstance(raw, str):
        raw = "".join([chunk async for chunk in raw])
    mode = _response_mode(teacher_text, detected_language)
    if mode == "nepali":
        return await enforce_pure_nepali_reply(raw, http)
    return _postprocess_multilingual_reply(raw)
