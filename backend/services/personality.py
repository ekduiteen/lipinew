"""Personality engine: deterministic response planning for LIPI's character."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from services.curriculum import QuestionPlan
from services.hearing import HearingResult
from services.turn_interpreter import TurnInterpretation


_DIRECT_CHOICE_PHRASES = {
    "everyday_basics": "\"How are you?\"",
    "friendship_informal": "\"What’s up?\"",
    "family_home": "\"Come eat.\"",
    "food_cooking": "\"Have you eaten?\"",
    "school_work": "\"Please sit down.\"",
    "instructions_requests": "\"Come here.\"",
    "emotions_comfort": "\"Are you okay?\"",
    "conflict_scolding": "\"Don’t do that.\"",
    "culture_ritual": "\"Namaste.\"",
    "regional_variation": "\"hello\"",
    "story_memory": "\"Once, when I was small...\"",
    "humor_playfulness": "\"You’re teasing me.\"",
}


@dataclass(frozen=True)
class ResponsePlan:
    acknowledgement: str
    learned_point: str | None
    question_goal: str
    question_type: str
    tone_style: str
    max_sentences: int
    must_confirm: bool
    must_ask_repeat: bool

    def to_prompt_block(self) -> str:
        learned_line = self.learned_point or "none"
        return (
            "## Response plan\n"
            f"- Acknowledgement: {self.acknowledgement}\n"
            f"- Learned point: {learned_line}\n"
            f"- Question goal: {self.question_goal}\n"
            f"- Question type: {self.question_type}\n"
            f"- Tone style: {self.tone_style}\n"
            f"- Max sentences: {self.max_sentences}\n"
            f"- Must confirm: {str(self.must_confirm).lower()}\n"
            f"- Must ask repeat: {str(self.must_ask_repeat).lower()}\n"
        )

    def to_dict(self) -> dict:
        return asdict(self)


def build_clarification_reply(hearing: HearingResult) -> str:
    if hearing.quality_label == "low":
        if hearing.mode == "english":
            return "I didn't quite catch that. Can you say it once more?"
        if hearing.mode == "mixed":
            return "म अलि बुझिनँ. Can you say that once more?"
        return "म अलि बुझिनँ। फेरि भन्न सक्छौ?"

    snippet = " ".join(hearing.clean_text.split()[:7]).strip(" ,")
    if hearing.mode == "english":
        return f"It sounds like you meant '{snippet}'. Is that right?" if snippet else "I only caught part of that. Is that right?"
    if hearing.mode == "mixed":
        return f"तिमीले '{snippet}' भन्न खोज्यौ जस्तो लाग्यो. Right?" if snippet else "तिमीले के भन्न खोज्यौ जस्तो लाग्यो. Right?"
    return f"तिमीले '{snippet}' भन्न खोज्यौ जस्तो लाग्यो, है?" if snippet else "तिमीले के भन्न खोज्यौ जस्तो लाग्यो, है?"


def build_direct_choice_reply(
    hearing: HearingResult,
    question_plan: QuestionPlan,
    *,
    target_language: str,
) -> str:
    target = target_language.strip() or "the language"
    topic_phrase = _DIRECT_CHOICE_PHRASES.get(question_plan.topic_key, "\"How are you?\"")

    if question_plan.question_type == "regional_variant":
        if hearing.mode == "english":
            return f"Okay. Is there a local {target} way to say {topic_phrase} where you're from?"
        if hearing.mode == "mixed":
            return f"ओके. तिम्रो ठाउँमा {topic_phrase} भन्न अर्को {target} तरिका छ?"
        return f"ठिक छ। तिम्रो ठाउँमा {topic_phrase} भन्न अर्को {target} तरिका छ?"

    if question_plan.question_type == "what_do_friends_say":
        if hearing.mode == "english":
            return f"Okay. In {target}, what do friends usually say instead of {topic_phrase}?"
        if hearing.mode == "mixed":
            return f"ओके. {target} मा साथीहरूले {topic_phrase} को सट्टा के भन्छन्?"
        return f"ठिक छ। {target} मा साथीहरूले {topic_phrase} को सट्टा के भन्छन्?"

    if question_plan.question_type == "what_do_elders_say":
        if hearing.mode == "english":
            return f"Okay. In {target}, what would elders say instead of {topic_phrase}?"
        if hearing.mode == "mixed":
            return f"ओके. {target} मा ठूला मान्छेले {topic_phrase} को सट्टा के भन्छन्?"
        return f"ठिक छ। {target} मा ठूला मान्छेले {topic_phrase} को सट्टा के भन्छन्?"

    if question_plan.question_type == "when_is_this_used":
        if hearing.mode == "english":
            return f"Okay. In {target}, when do people actually use {topic_phrase}?"
        if hearing.mode == "mixed":
            return f"ओके. {target} मा {topic_phrase} कहिले प्रयोग हुन्छ?"
        return f"ठिक छ। {target} मा {topic_phrase} कहिले प्रयोग हुन्छ?"

    if hearing.mode == "english":
        return f"Okay. How do you say {topic_phrase} in {target}?"
    if hearing.mode == "mixed":
        return f"ओके. {topic_phrase} {target} मा कसरी भन्छन्?"
    return f"ठिक छ। {topic_phrase} {target} मा कसरी भन्छन्?"


def build_response_plan(
    hearing: HearingResult,
    interpretation: TurnInterpretation,
    question_plan: QuestionPlan,
    memory: dict,
) -> ResponsePlan:
    user_style = memory.get("user_style") or "neutral"
    tone_style = "warm_social"
    if user_style == "formal" or interpretation.register_hint == "tapai":
        tone_style = "warm_respectful"
    elif user_style == "casual":
        tone_style = "casual_playful"

    if interpretation.is_correction:
        acknowledgement = "Accept the correction in one short natural line and restate the correct form."
        learned_point = interpretation.taught_terms[0] if interpretation.taught_terms else memory.get("last_correction")
        question_goal = "Go one level deeper after the correction."
        must_confirm = False
    elif interpretation.intent_type == "invite_lipi_choice":
        acknowledgement = "Accept briefly and naturally without repeating the teacher's exact words back to them."
        learned_point = memory.get("last_taught_word")
        question_goal = "Choose one concrete thing you want to learn now and ask it directly in one natural question."
        must_confirm = False
    elif hearing.quality_label == "medium":
        acknowledgement = "Reflect the likely meaning cautiously."
        learned_point = None
        question_goal = "Confirm what the teacher meant."
        must_confirm = True
    elif interpretation.intent_type == "chat_socially":
        acknowledgement = "React to the teacher's feeling or social meaning first."
        learned_point = None
        question_goal = "Keep the conversation moving naturally."
        must_confirm = False
    elif interpretation.intent_type == "teach_word":
        acknowledgement = "Restate the taught meaning briefly without thanking or sounding formal."
        learned_point = interpretation.taught_terms[0] if interpretation.taught_terms else memory.get("last_taught_word")
        question_goal = "Ask about usage, register, or context."
        must_confirm = False
    else:
        acknowledgement = "Acknowledge the teacher's meaning in one short spoken line."
        learned_point = memory.get("last_taught_word")
        question_goal = "Ask one useful follow-up tied to the current topic."
        must_confirm = False

    return ResponsePlan(
        acknowledgement=acknowledgement,
        learned_point=learned_point,
        question_goal=question_goal,
        question_type=question_plan.question_type,
        tone_style=tone_style,
        max_sentences=2,
        must_confirm=must_confirm,
        must_ask_repeat=hearing.quality_label == "low",
    )
