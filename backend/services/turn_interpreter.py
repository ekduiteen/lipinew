"""Turn interpreter: infer intent, correction, topic, and social style from a hearing result."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re

from services.hearing import HearingResult


_TERM_RE = re.compile(r"[\u0900-\u097F]+|[A-Za-z]+(?:'[A-Za-z]+)?")
_TEACH_WORD_HINTS = ("how do you say", "means", "भनेको", "भन्ने", "say this")
_CORRECTION_HINTS = ("होइन", "यसरी भनिन्छ", "correct is", "not like that", "say it like")
_EXAMPLE_HINTS = ("example", "उदाहरण", "वाक्य", "sentence")
_REGIONAL_HINTS = ("newari", "maithili", "bhojpuri", "तिम्रो ठाउँ", "region", "dialect", "local")
_SOCIAL_HINTS = ("friend", "sathi", "साथी", "hangout", "joke", "fun")
_EMOTION_HINTS = ("happy", "sad", "angry", "खुसी", "दुखी", "रिस", "लाग्यो")
_QUESTION_HINTS = ("?", "कसरी", "किन", "what", "how", "why", "when")
_INVITE_CHOICE_HINTS = (
    "what do you want to learn",
    "what do you want me to teach",
    "what should i teach you",
    "ask me what you want to learn",
    "what do you want to know",
    "what do you want",
    "के सिक्न चाहन्छौ",
    "के सिक्न चाहन्छ्यौ",
    "के सिक्न चाहनुहुन्छ",
    "के सिकाऊँ",
    "के सिकाउने",
    "के जान्न चाहन्छौ",
    "के जान्न चाहन्छ्यौ",
    "के चाहिन्छ",
)


@dataclass(frozen=True)
class TurnInterpretation:
    intent_type: str
    active_topic: str
    is_correction: bool
    taught_terms: list[str]
    register_hint: str
    emotion_hint: str | None
    user_goal: str
    candidate_followup_zones: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _extract_terms(text: str) -> list[str]:
    terms: list[str] = []
    for token in _TERM_RE.findall(text):
        normalized = token.strip().lower()
        if len(normalized) < 2:
            continue
        if normalized not in terms:
            terms.append(normalized)
        if len(terms) >= 5:
            break
    return terms


def interpret_turn(hearing: HearingResult, memory: dict | None = None) -> TurnInterpretation:
    memory = memory or {}
    text = hearing.clean_text
    lowered = text.lower()
    is_correction = any(marker in lowered for marker in _CORRECTION_HINTS)

    if any(hint in lowered for hint in _INVITE_CHOICE_HINTS):
        intent_type = "invite_lipi_choice"
    elif any(hint in lowered for hint in _TEACH_WORD_HINTS):
        intent_type = "teach_word"
    elif is_correction:
        intent_type = "correct_meaning"
    elif any(hint in lowered for hint in _EXAMPLE_HINTS):
        intent_type = "give_example"
    elif any(hint in lowered for hint in _REGIONAL_HINTS):
        intent_type = "regional_variation"
    elif any(hint in lowered for hint in _QUESTION_HINTS):
        intent_type = "ask_question"
    elif any(hint in lowered for hint in _SOCIAL_HINTS + _EMOTION_HINTS):
        intent_type = "chat_socially"
    else:
        intent_type = "unknown"

    if any(hint in lowered for hint in _REGIONAL_HINTS):
        active_topic = "regional_variation"
    elif any(hint in lowered for hint in _SOCIAL_HINTS):
        active_topic = "friendship_informal"
    elif any(hint in lowered for hint in _EMOTION_HINTS):
        active_topic = "emotions_comfort"
    else:
        active_topic = (memory.get("recent_topics") or ["everyday_basics"])[0]

    if "हजुर" in text or "तपाईं" in text:
        register_hint = "tapai"
    elif "तिमी" in text:
        register_hint = "timi"
    elif "तँ" in text:
        register_hint = "ta"
    else:
        register_hint = memory.get("user_style") == "formal" and "tapai" or "timi"

    emotion_hint = None
    if any(token in lowered for token in ("happy", "खुसी")):
        emotion_hint = "positive"
    elif any(token in lowered for token in ("sad", "दुख", "hurt")):
        emotion_hint = "sad"
    elif any(token in lowered for token in ("angry", "रिस")):
        emotion_hint = "angry"

    taught_terms = _extract_terms(text) if intent_type in {"teach_word", "correct_meaning", "give_example"} else []

    if is_correction:
        user_goal = "correct_lipi"
        candidate_followup_zones = ["contrast", "usage", "register"]
    elif intent_type == "invite_lipi_choice":
        user_goal = "let_lipi_choose"
        candidate_followup_zones = ["under_collected_gap", "translation", "usage"]
    elif intent_type == "teach_word":
        user_goal = "teach_language"
        candidate_followup_zones = ["usage", "example", "register"]
    elif intent_type == "regional_variation":
        user_goal = "share_regional_form"
        candidate_followup_zones = ["regional", "contrast", "social"]
    elif intent_type == "chat_socially":
        user_goal = "social_chat"
        candidate_followup_zones = ["social", "emotion", "story"]
    elif intent_type == "ask_question":
        user_goal = "get_answer"
        candidate_followup_zones = ["direct_answer", "clarify_usage"]
    else:
        user_goal = "continue_conversation"
        candidate_followup_zones = ["example", "scenario", "usage"]

    return TurnInterpretation(
        intent_type=intent_type,
        active_topic=active_topic,
        is_correction=is_correction,
        taught_terms=taught_terms,
        register_hint=register_hint,
        emotion_hint=emotion_hint,
        user_goal=user_goal,
        candidate_followup_zones=candidate_followup_zones,
    )
