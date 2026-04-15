"""Post-generation control for language, tone, repetition, and weak-student behavior."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from services.behavior_policy import BehaviorPolicy
from services.hearing import HearingResult
from services.input_understanding import InputUnderstanding


_MULTISPACE_RE = re.compile(r"\s+")
_WEAK_STUDENT_PHRASES = (
    "teach me more",
    "tell me more",
    "can you explain further",
    "i will continue learning",
    "you are teaching me",
    "i am excited to learn",
    "तपाईंले मलाई सिकाउनुभयो",
    "मलाई अझ सिकाउनुहोस्",
    "म सिक्नको लागि",
)
_ROBOTIC_PHRASES = (
    "that is very interesting",
    "i understand,",
    "oh, i understand",
    "मलाई धेरै रमाइलो लाग्यो",
)
_HINDI_MARKERS = ("कैसे", "क्या", "है", "लेकिन", "नहीं")
_GENERIC_LOW_VALUE_QUESTIONS = (
    "teach me more",
    "tell me more",
    "what else",
    "can you explain more",
    "अरू के",
    "अझ सिकाऊ",
    "थप बताऊ",
)


@dataclass(frozen=True)
class GuardResult:
    action: str
    text: str
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?।])\s+", text) if part.strip()]


def _fallback_safe_response(hearing: HearingResult, policy: BehaviorPolicy) -> str:
    if policy.response_language == "en" or hearing.mode == "english":
        return "Okay. Can you say that in one simple way?"
    if hearing.mode == "mixed":
        return "ओके। यो एकचोटि सजिलोसँग भन्न सक्छौ?"
    return "ठिक छ। यो एकचोटि सजिलोसँग भन्न सक्छौ?"


def guard_response(
    text: str,
    *,
    hearing: HearingResult,
    understanding: InputUnderstanding,
    policy: BehaviorPolicy,
) -> GuardResult:
    reasons: list[str] = []
    cleaned = _MULTISPACE_RE.sub(" ", text.replace("\n", " ")).strip()

    lowered = cleaned.lower()
    if any(phrase in lowered for phrase in _WEAK_STUDENT_PHRASES):
        reasons.append("weak_student_behavior")
    if any(phrase in lowered for phrase in _ROBOTIC_PHRASES):
        reasons.append("robotic_tone")
    if any(phrase in lowered for phrase in _GENERIC_LOW_VALUE_QUESTIONS):
        reasons.append("generic_followup")
    if policy.response_language == "ne" and any(marker in lowered for marker in _HINDI_MARKERS):
        reasons.append("language_purity_risk")

    sentence_parts = _sentences(cleaned)
    if len(sentence_parts) > 2:
        sentence_parts = sentence_parts[:2]
        reasons.append("too_many_sentences")
    cleaned = " ".join(sentence_parts).strip()

    if cleaned.count("?") > 1:
        first_q = cleaned.find("?")
        cleaned = cleaned[: first_q + 1] + cleaned[first_q + 1 :].replace("?", "")
        reasons.append("too_many_questions")

    if understanding.is_correction and policy.confirmation_style != "correction_accept":
        reasons.append("correction_style_mismatch")
    if policy.politeness_level == "high" and any(token in lowered for token in ("तँ", "bro", "buddy")):
        reasons.append("politeness_mismatch")

    if any(reason in reasons for reason in ("weak_student_behavior", "language_purity_risk", "generic_followup", "politeness_mismatch")):
        if policy.response_language == "en":
            rewritten = "Got it. What would be the natural way to say that?"
        else:
            rewritten = "ठिक छ। यसलाई स्वाभाविक रूपमा कसरी भन्छन्?"
        return GuardResult(action="rewrite", text=rewritten, reasons=reasons)

    if not cleaned:
        return GuardResult(action="fallback", text=_fallback_safe_response(hearing, policy), reasons=["empty_after_cleanup"])

    return GuardResult(action="approve", text=cleaned, reasons=reasons)
