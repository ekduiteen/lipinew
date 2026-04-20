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


def _trim_generic_followup(text: str) -> str:
    sentences = _sentences(text)
    if not sentences:
        return text.strip()

    filtered: list[str] = []
    removed = False
    for sentence in sentences:
        lowered = sentence.lower()
        if any(phrase in lowered for phrase in _GENERIC_LOW_VALUE_QUESTIONS):
            removed = True
            continue
        filtered.append(sentence)

    if filtered:
        return " ".join(filtered).strip()
    if removed:
        return ""
    return text.strip()


def _fallback_safe_response(hearing: HearingResult, policy: BehaviorPolicy) -> str:
    if policy.response_language == "en" or hearing.mode == "english":
        return "Okay. Can you say that in one simple way?"
    if hearing.mode == "mixed":
        return "ओके। यो एकचोटि सजिलोसँग भन्न सक्छौ?"
    return "ठिक छ। यो एकचोटि सजिलोसँग भन्न सक्छौ?"


def _rewrite_from_policy(hearing: HearingResult, policy: BehaviorPolicy) -> str:
    family = policy.prompt_family
    if policy.response_language == "en" or hearing.mode == "english":
        mapping = {
            "ask_target_language": f"Ohh okay… how would you say that in {policy.teach_language.upper()}?",
            "ask_natural_way": "Ohh okay… what's the natural way to say that?",
            "confirm_meaning": "Ohh okay… so that means what you said there, right?",
            "ask_example": "Ohh okay. Can you give one simple example?",
            "ask_register_variant": "Ohh okay. Is there a more casual way to say it too?",
            "ask_local_variant": "Ohh okay. Is there a more local way to say that?",
            "ask_simple_rephrase": "Wait, can you say the same thing in easier words?",
            "ask_full_sentence": "Wait, can you say it once as a full sentence?",
        }
        return mapping.get(family, "Ohh okay… what's the natural way to say that?")
    if hearing.mode == "mixed":
        mapping = {
            "ask_target_language": f"ओह ठीक छ… यो {policy.teach_language.upper()} मा कसरी भन्छन्?",
            "ask_natural_way": "ओह ठीक छ… natural तरिकाले कसरी भन्छन्?",
            "confirm_meaning": "ओह ठीक छ… भनेपछि त्यसको मतलब यही हो, है?",
            "ask_example": "ओह ठीक छ। एउटा सजिलो example दिन सक्छौ?",
            "ask_register_variant": "ओह ठीक छ। अलि casual तरिकाले पनि भन्छन्?",
            "ask_local_variant": "ओह ठीक छ। अलि local तरिकाले पनि भन्छन्?",
            "ask_simple_rephrase": "ओह ठीक छ। यही कुरा अझ सजिलो शब्दमा भन्न सक्छौ?",
            "ask_full_sentence": "wait, यो एकपटक पुरा वाक्यमा भन्न सक्छौ?",
        }
        return mapping.get(family, "ओह ठीक छ… natural तरिकाले कसरी भन्छन्?")

    mapping = {
        "ask_target_language": f"ओह ठीक छ… यो {policy.teach_language.upper()} मा कसरी भन्छन्?",
        "ask_natural_way": "ओह ठीक छ… स्वाभाविक रूपमा कसरी भन्छन्?",
        "confirm_meaning": "ओह ठीक छ… भनेपछि त्यसको मतलब यही हो, है?",
        "ask_example": "ओह ठीक छ। एउटा सजिलो उदाहरण दिन सक्छौ?",
        "ask_register_variant": "ओह ठीक छ। अलि casual तरिकाले पनि भन्छन्?",
        "ask_local_variant": "ओह ठीक छ। अलि स्थानीय तरिकाले पनि भन्छन्?",
        "ask_simple_rephrase": "ओह ठीक छ। यही कुरा अझ सजिलो शब्दमा भन्न सक्छौ?",
        "ask_full_sentence": "पर्ख… यो एकपटक पुरा वाक्यमा भन्न सक्छौ?",
    }
    return mapping.get(family, "ओह ठीक छ… स्वाभाविक रूपमा कसरी भन्छन्?")


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

    hard_rewrite_reasons = {"weak_student_behavior", "language_purity_risk", "politeness_mismatch"}
    if any(reason in reasons for reason in hard_rewrite_reasons):
        rewritten = _rewrite_from_policy(hearing, policy)
        return GuardResult(action="rewrite", text=rewritten, reasons=reasons)

    if "generic_followup" in reasons:
        cleaned = _trim_generic_followup(cleaned)
        if cleaned:
            return GuardResult(action="approve", text=cleaned, reasons=reasons)

    if not cleaned:
        return GuardResult(action="fallback", text=_fallback_safe_response(hearing, policy), reasons=["empty_after_cleanup"])

    return GuardResult(action="approve", text=cleaned, reasons=reasons)
