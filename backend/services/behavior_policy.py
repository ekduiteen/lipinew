"""
Behavior Policy Engine for LIPI Teach Mode.

This engine decides on every turn:
1. What mode LIPI should operate in (friend, student, brainstorm, chat, teach)
2. What language LIPI should reply in
3. Whether and how to steer toward target language
4. What kind of elicitation, confirmation, or expansion to pursue
5. How to handle unclear expressions

The engine takes structured turn analysis and outputs a comprehensive policy
object that guides prompt construction and response generation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from services.input_understanding import InputUnderstanding
from services.memory_service import StructuredSessionMemory
from services.teacher_modeling import TeacherModel


# ─── Constants and Enums ─────────────────────────────────────────────────────

class ReplyMode:
    """Mode determines conversational behavior overlay."""
    TEACH = "teach"  # default for teach screen, target language extraction active
    FRIEND = "friend"  # warm, softer, may still steer toward target language
    STUDENT = "student"  # slightly unsure, invites correction
    BRAINSTORM = "brainstorm"  # creative/planning mode, collaborative
    CHAT = "chat"  # general knowledge Q&A, brief, helpful


class ReplyLanguage:
    """Language of LIPI's response."""
    ENGLISH = "en"
    NEPALI = "ne"
    TARGET = "target"  # use teach language
    MIXED = "mixed"  # blend bridge + target


class SteeringStrength:
    """How directly to guide toward target language."""
    NONE = "none"  # no steering this turn
    SOFT = "soft"  # gentle, one turn away
    MEDIUM = "medium"  # more direct
    STRONG = "strong"  # persistent, multiple turns without target


class ElicitationGoal:
    """What kind of target-language output to ask for."""
    NONE = "none"
    WORD = "word"  # single-word equivalent
    PHRASE = "phrase"  # common phrase or short expression
    SENTENCE = "sentence"  # full sentence naturally said
    VARIANT = "variant"  # casual/formal/local alternative
    MEANING = "meaning"  # what does unclear target-language expression mean?
    CORRECTION = "correction"  # how to fix/correct previous attempt
    USAGE_CONTEXT = "usage_context"  # when/with whom/in what situation


class ConfirmationGoal:
    """What to confirm about target-language output."""
    NONE = "none"
    MEANING_CHECK = "meaning_check"  # does this mean...?
    NATURALNESS_CHECK = "naturalness_check"  # do people actually say it like that?
    VARIANT_CHECK = "variant_check"  # is there another way?


class UnclearExpressionStrategy:
    """How to handle slang, metaphor, or ambiguous expressions."""
    INFER_AND_CONFIRM = "infer_and_confirm"  # guess meaning and confirm
    ASK_MEANING = "ask_meaning"  # ask directly what it means
    DEFER = "defer"  # skip for now, mark for later


# ─── Policy Dataclass ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class BehaviorPolicy:
    """Comprehensive policy decision for one turn in Teach Mode."""

    # Language layers
    conversation_language: str  # detected language user is speaking in
    teach_language: str  # normalized target language (ne, new, mai, etc.)
    response_language: str  # which language LIPI should reply in

    # Target language presence
    target_language_present: bool  # does user's input contain target language?

    # Mode and steering
    reply_mode: str  # friend, student, brainstorm, chat, teach
    steer_to_target_language: bool  # should this turn guide toward target language?
    steering_strength: str  # none, soft, medium, strong

    # Turn goals
    turn_goal: str  # legacy: ELICIT_TARGET, CONFIRM_AND_EXPAND, ACCEPT_AND_MOVE, CLARIFY_MEANING
    prompt_family: str  # legacy: ask_natural_way, confirm_meaning, etc.

    # Elicitation and confirmation
    elicitation_goal: str  # word, phrase, sentence, variant, meaning, correction, usage_context
    confirmation_goal: str  # meaning_check, naturalness_check, variant_check
    should_expand: bool  # ask for variants or examples after confirmation?
    should_ask_followup: bool  # should this turn include a question?
    max_followups: int  # how many questions max per response (usually 1)

    # Unclear expression handling
    handle_unclear_expression: bool  # is there slang/metaphor to address?
    unclear_expression_strategy: str  # infer_and_confirm, ask_meaning, defer

    # Behavioral nuance
    mirror_code_switching: bool  # should LIPI match user's code-switching?
    register: str  # formal register to use (tapai, timi, ta, hajur, etc.)
    tone_style: str  # curious_warm, respectful_accepting, careful_listening, etc.
    uncertainty_level: float  # 0.0–1.0, how unsure should LIPI sound?
    curiosity_level: float  # 0.0–1.0, how interested/engaged?
    confirmation_style: str  # light_ack, inference_first, correction_accept, repair, ask_repeat
    allowed_humor: float  # 0.0–1.0, how much joking is appropriate?
    infer_vs_ask: str  # infer or ask (when uncertain)
    dialect_alignment: str  # which dialect/variant to align with
    politeness_level: str  # high, medium, low

    # Prompt flags consumed by prompt_builder
    be_warm: bool = True
    be_concise: bool = True
    act_slightly_unsure: bool = True
    avoid_long_explanations: bool = True
    ask_at_most_one_question: bool = True
    treat_bridge_language_as_scaffolding: bool = True
    prioritize_target_language_elicitation: bool = True
    confirm_before_expanding: bool = True
    be_conversational_not_robotic: bool = True

    def to_dict(self) -> dict:
        """Export policy as dictionary."""
        return asdict(self)

    def to_prompt_block(self) -> str:
        """Export policy as formatted text block for system prompt."""
        return (
            "## Behavior Policy\n"
            f"- Reply mode: {self.reply_mode}\n"
            f"- Reply language: {self.response_language}\n"
            f"- Conversation language: {self.conversation_language}\n"
            f"- Teach language: {self.teach_language}\n"
            f"- Target language present: {str(self.target_language_present).lower()}\n"
            f"- Steer to target language: {str(self.steer_to_target_language).lower()}\n"
            f"- Steering strength: {self.steering_strength}\n"
            f"- Elicitation goal: {self.elicitation_goal}\n"
            f"- Confirmation goal: {self.confirmation_goal}\n"
            f"- Should expand: {str(self.should_expand).lower()}\n"
            f"- Should ask followup: {str(self.should_ask_followup).lower()}\n"
            f"- Max followups: {self.max_followups}\n"
            f"- Register: {self.register}\n"
            f"- Tone style: {self.tone_style}\n"
            f"- Uncertainty level: {self.uncertainty_level:.2f}\n"
            f"- Curiosity level: {self.curiosity_level:.2f}\n"
            f"- Politeness level: {self.politeness_level}\n"
            f"- Be warm: {str(self.be_warm).lower()}\n"
            f"- Be concise: {str(self.be_concise).lower()}\n"
            f"- Ask at most one question: {str(self.ask_at_most_one_question).lower()}\n"
        )


# ─── Helper Functions ───────────────────────────────────────────────────────

def _normalize_language_key(language: str | None) -> str:
    """Normalize language names to canonical 2-letter codes."""
    lowered = str(language or "").strip().lower()
    if lowered in {"new", "newa", "newar", "newari", "nepal bhasa"}:
        return "new"
    if lowered in {"ne", "nepali"}:
        return "ne"
    if lowered in {"en", "english"}:
        return "en"
    return lowered or "ne"


def _infer_conversation_language(understanding: InputUnderstanding) -> str:
    """Detect which language(s) user is currently speaking."""
    primary = _normalize_language_key(understanding.primary_language)
    if understanding.code_switch_ratio >= 0.25 and understanding.secondary_languages:
        return "mixed"
    return primary


def _target_language_present(understanding: InputUnderstanding, teach_language: str) -> bool:
    """Check if user actually used the target language in their input."""
    teach_key = _normalize_language_key(teach_language)
    if _normalize_language_key(understanding.primary_language) == teach_key:
        return True
    if any(_normalize_language_key(lang) == teach_key for lang in understanding.secondary_languages):
        return True
    return False


def _reply_prompt_family(reply: str) -> str:
    """Infer which prompt family was used from assistant's previous reply."""
    lowered = str(reply or "").strip().lower()
    if not lowered:
        return "none"
    if "natural way" in lowered or "स्वाभाविक" in lowered:
        return "ask_natural_way"
    if "simple example" in lowered or "उदाहरण" in lowered:
        return "ask_example"
    if "full sentence" in lowered or "पुरा वाक्य" in lowered:
        return "ask_full_sentence"
    if "easier words" in lowered or "सजिलो शब्द" in lowered:
        return "ask_simple_rephrase"
    if "that means" in lowered or "means" in lowered or "भनेको" in lowered:
        return "confirm_meaning"
    if "local way" in lowered or "local" in lowered or "ठाउँमा" in lowered:
        return "ask_local_variant"
    if "formal" in lowered or "casual" in lowered or "सम्मान" in lowered:
        return "ask_register_variant"
    if "how do you say" in lowered or "कसरी भन्छन्" in lowered:
        return "ask_target_language"
    return "generic_followup"


def _choose_turn_goal(
    *,
    understanding: InputUnderstanding,
    target_language_present: bool,
) -> str:
    """Decide primary turn goal (legacy field, kept for compatibility)."""
    if understanding.is_correction:
        return "ACCEPT_AND_MOVE"
    if understanding.intent_label in {"pronunciation_guidance", "register_instruction"}:
        return "CONFIRM_AND_EXPAND"
    if not target_language_present:
        if understanding.intent_label in {"low_signal", "unknown", "clarification", "confirmation"}:
            return "CLARIFY_MEANING"
        return "ELICIT_TARGET"
    return "CONFIRM_AND_EXPAND"


def _choose_prompt_family(
    *,
    turn_goal: str,
    understanding: InputUnderstanding,
    recent_assistant_replies: list[str],
) -> str:
    """Choose which prompt template family to use, avoiding repetition."""
    recent_families = [_reply_prompt_family(reply) for reply in recent_assistant_replies]

    def _pick(candidates: list[str]) -> str:
        for candidate in candidates:
            if candidate not in recent_families:
                return candidate
        return candidates[0]

    if turn_goal == "ACCEPT_AND_MOVE":
        return _pick(["confirm_meaning", "ask_example", "ask_register_variant"])
    if turn_goal == "CLARIFY_MEANING":
        return _pick(["ask_simple_rephrase", "ask_example", "ask_full_sentence"])
    if turn_goal == "ELICIT_TARGET":
        if understanding.code_switch_ratio >= 0.25:
            return _pick(["ask_target_language", "ask_natural_way", "ask_local_variant"])
        return _pick(["ask_natural_way", "ask_target_language", "ask_example"])
    return _pick(["confirm_meaning", "ask_example", "ask_register_variant", "ask_local_variant"])


def _decide_reply_mode(
    *,
    understanding: InputUnderstanding,
    target_language_present: bool,
    teaching_style: str,
) -> str:
    """Decide the conversational mode/tone for this turn."""
    # Corrections are always in student mode (grateful, slightly unsure)
    if understanding.is_correction:
        return ReplyMode.STUDENT

    # Teachings explicitly requested invite student mode
    if understanding.is_teaching:
        return ReplyMode.STUDENT

    # Pronunciation/register guidance → student mode
    if understanding.intent_label in {"pronunciation_guidance", "register_instruction"}:
        return ReplyMode.STUDENT

    # Already have target language → switch to teacher-as-student mode
    if target_language_present:
        return ReplyMode.STUDENT

    # User sharing about life/feelings → friend mode
    if understanding.intent_label in {"casual_sharing", "emotional_expression", "personal_reflection"}:
        return ReplyMode.FRIEND

    # Planning/brainstorming/naming → brainstorm mode
    if understanding.intent_label in {"brainstorm_ideas", "ask_for_naming", "planning"}:
        return ReplyMode.BRAINSTORM

    # General knowledge questions → chat mode (but soft redirect to target language later)
    if understanding.intent_label in {"general_question", "ask_explanation", "knowledge_request"}:
        return ReplyMode.CHAT

    # Default: teach mode
    return ReplyMode.TEACH


def _decide_steering(
    *,
    target_language_present: bool,
    conversation_language: str,
    teach_language: str,
    recent_turns_without_target: int,
    user_resistance_score: float,
) -> tuple[bool, str]:
    """
    Decide whether to steer toward target language and how strongly.

    Returns: (should_steer, strength)
    """
    # Rule 1: Already using target language → don't steer this turn
    if target_language_present:
        return False, SteeringStrength.NONE

    # Rule 5: User is resisting → soften steering
    if user_resistance_score >= 0.7:
        return True, SteeringStrength.SOFT

    # Rule 2: Stay in bridge language too long → increase steering
    if recent_turns_without_target >= 3:
        if recent_turns_without_target >= 5:
            return True, SteeringStrength.STRONG
        return True, SteeringStrength.MEDIUM

    # Default: soft steering in bridge language
    return True, SteeringStrength.SOFT


def _decide_elicitation_goal(
    *,
    turn_goal: str,
    understanding: InputUnderstanding,
    target_language_present: bool,
) -> str:
    """Decide what kind of target-language output to ask for."""
    if target_language_present:
        return ElicitationGoal.NONE

    if turn_goal == "ACCEPT_AND_MOVE":
        return ElicitationGoal.NONE

    if turn_goal == "CLARIFY_MEANING":
        return ElicitationGoal.PHRASE

    if turn_goal == "ELICIT_TARGET":
        # Heuristic: length of bridge-language input determines elicitation depth
        word_count = len((understanding.taught_terms or []))
        if word_count == 0:
            return ElicitationGoal.WORD
        if word_count <= 3:
            return ElicitationGoal.PHRASE
        return ElicitationGoal.SENTENCE

    return ElicitationGoal.NONE


def _decide_confirmation_goal(
    *,
    target_language_present: bool,
    understanding: InputUnderstanding,
) -> str:
    """Decide what aspect of target-language output to confirm."""
    if not target_language_present:
        return ConfirmationGoal.NONE

    # High-quality teaching input → ask for variants/naturalness
    if understanding.transcript_confidence >= 0.92 and understanding.is_teaching:
        return ConfirmationGoal.NATURALNESS_CHECK

    # Correction → confirm meaning
    if understanding.is_correction:
        return ConfirmationGoal.MEANING_CHECK

    # Standard → meaning check
    return ConfirmationGoal.MEANING_CHECK


def _decide_unclear_strategy(
    *,
    understanding: InputUnderstanding,
    detected_confidence: float,
) -> tuple[bool, str]:
    """Decide how to handle slang, metaphor, or unclear expressions."""
    has_unclear = (
        understanding.emotion not in {"neutral", "positive"}
        or understanding.intent_label in {"slang_usage", "metaphor", "idiomatic_expression"}
    )

    if not has_unclear:
        return False, UnclearExpressionStrategy.DEFER

    if detected_confidence >= 0.7:
        return True, UnclearExpressionStrategy.INFER_AND_CONFIRM

    if 0.4 <= detected_confidence < 0.7:
        return True, UnclearExpressionStrategy.ASK_MEANING

    return True, UnclearExpressionStrategy.DEFER


# ─── Regular LLM Mode (Testing) ─────────────────────────────────────────────

def _create_neutral_policy(
    *,
    understanding: InputUnderstanding,
    teach_language: str,
) -> BehaviorPolicy:
    """
    Create a neutral policy for regular LLM mode (no teach mode behaviors).
    Useful for testing without extraction-focused steering.
    """
    return BehaviorPolicy(
        conversation_language=_infer_conversation_language(understanding),
        teach_language=_normalize_language_key(teach_language),
        response_language=understanding.primary_language or "ne",
        target_language_present=False,
        reply_mode=ReplyMode.CHAT,
        steer_to_target_language=False,
        steering_strength=SteeringStrength.NONE,
        turn_goal="CLARIFY_MEANING",
        prompt_family="generic_followup",
        elicitation_goal=ElicitationGoal.NONE,
        confirmation_goal=ConfirmationGoal.NONE,
        should_expand=False,
        should_ask_followup=False,
        max_followups=0,
        handle_unclear_expression=False,
        unclear_expression_strategy=UnclearExpressionStrategy.DEFER,
        mirror_code_switching=False,
        register="tapai",
        tone_style="neutral",
        uncertainty_level=0.1,
        curiosity_level=0.5,
        confirmation_style="light_ack",
        allowed_humor=0.05,
        infer_vs_ask="infer",
        dialect_alignment="neutral",
        politeness_level="medium",
        be_warm=False,
        be_concise=False,
        act_slightly_unsure=False,
        avoid_long_explanations=False,
        ask_at_most_one_question=False,
        treat_bridge_language_as_scaffolding=False,
        prioritize_target_language_elicitation=False,
        confirm_before_expanding=False,
        be_conversational_not_robotic=False,
    )


# ─── Main Policy Decision Engine ────────────────────────────────────────────

def choose_behavior_policy(
    *,
    teacher_model: TeacherModel,
    session_memory: StructuredSessionMemory,
    correction_count_recent: int,
    understanding: InputUnderstanding,
    target_language: str,
    recent_assistant_replies: list[str] | None = None,
    recent_turns_without_target: int = 0,
    user_resistance_score: float = 0.0,
    teach_mode_enabled: bool = True,
) -> BehaviorPolicy:
    """
    Build comprehensive behavior policy for one turn in Teach Mode.

    This is the main decision engine. It synthesizes turn analysis into a
    structured policy object that guides prompt construction and response.

    Args:
        teacher_model: Teacher profile and credibility
        session_memory: Ongoing conversation state
        correction_count_recent: How many corrections in recent turns
        understanding: Analyzed input (language, intent, etc.)
        target_language: User's selected language to learn
        recent_assistant_replies: Last few LIPI responses (for repetition avoidance)
        recent_turns_without_target: Count of turns in bridge language without target
        user_resistance_score: 0.0–1.0, is user resisting target language?
        teach_mode_enabled: If False, returns neutral policy (regular LLM mode for testing)

    Returns:
        BehaviorPolicy: Comprehensive policy object
    """

    # If teach mode is disabled, return neutral policy (for testing)
    if not teach_mode_enabled:
        return _create_neutral_policy(
            understanding=understanding,
            teach_language=target_language,
        )

    # ─── Language detection ─────────────────────────────────────────────────
    conversation_language = _infer_conversation_language(understanding)
    teach_language = _normalize_language_key(target_language)
    target_language_present = _target_language_present(understanding, teach_language)

    # Decide what language to reply in
    if understanding.primary_language == "en":
        response_language = "en"
    elif understanding.primary_language in {"new", "newari"}:
        response_language = "ne"
    else:
        response_language = understanding.primary_language or "ne"

    # ─── Turn goal (legacy compatibility) ───────────────────────────────────
    turn_goal = _choose_turn_goal(
        understanding=understanding,
        target_language_present=target_language_present,
    )
    prompt_family = _choose_prompt_family(
        turn_goal=turn_goal,
        understanding=understanding,
        recent_assistant_replies=list(recent_assistant_replies or []),
    )

    # ─── Mode and steering ──────────────────────────────────────────────────
    reply_mode = _decide_reply_mode(
        understanding=understanding,
        target_language_present=target_language_present,
        teaching_style=teacher_model.teaching_style,
    )

    steer_to_target, steering_strength = _decide_steering(
        target_language_present=target_language_present,
        conversation_language=conversation_language,
        teach_language=teach_language,
        recent_turns_without_target=recent_turns_without_target,
        user_resistance_score=user_resistance_score,
    )

    # ─── Elicitation and confirmation ───────────────────────────────────────
    elicitation_goal = _decide_elicitation_goal(
        turn_goal=turn_goal,
        understanding=understanding,
        target_language_present=target_language_present,
    )

    confirmation_goal = _decide_confirmation_goal(
        target_language_present=target_language_present,
        understanding=understanding,
    )

    should_expand = target_language_present and confirmation_goal != ConfirmationGoal.NONE
    should_ask_followup = turn_goal in {"ELICIT_TARGET", "CONFIRM_AND_EXPAND"}

    # ─── Unclear expression handling ────────────────────────────────────────
    handle_unclear, unclear_strategy = _decide_unclear_strategy(
        understanding=understanding,
        detected_confidence=understanding.transcript_confidence,
    )

    # ─── Behavioral nuance ──────────────────────────────────────────────────
    mirror_code_switching = (
        understanding.code_switch_ratio >= 0.28 and teacher_model.teaching_style != "formal_guided"
    )

    uncertainty_level = max(0.05, min(1.0, 1.0 - understanding.transcript_confidence))
    if not understanding.conversation_allowed:
        uncertainty_level = max(uncertainty_level, 0.85)

    curiosity_level = 0.7
    if understanding.is_teaching:
        curiosity_level += 0.1
    if understanding.topic in {"regional_variation", "culture_ritual", "greeting_usage"}:
        curiosity_level += 0.1
    if correction_count_recent >= 2:
        curiosity_level -= 0.1
    curiosity_level = max(0.35, min(curiosity_level, 0.95))

    # Decide confirmation style
    if not understanding.conversation_allowed or understanding.intent_label == "low_signal":
        confirmation_style = "ask_repeat"
        infer_vs_ask = "ask"
    elif understanding.transcript_confidence < 0.74:
        confirmation_style = "inference_first"
        infer_vs_ask = "ask"
    elif understanding.is_correction:
        confirmation_style = "correction_accept"
        infer_vs_ask = "infer"
    elif understanding.intent_label == "register_instruction":
        confirmation_style = "light_ack"
        infer_vs_ask = "infer"
    elif understanding.intent_label == "pronunciation_guidance":
        confirmation_style = "repair"
        infer_vs_ask = "ask"
    else:
        confirmation_style = "light_ack"
        infer_vs_ask = "infer"

    # Humor level based on register and teaching style
    allowed_humor = 0.05
    if teacher_model.preferred_register in {"timi", "ta"} and teacher_model.teaching_style in {
        "steady_teacher",
        "multilingual_bridge",
    }:
        allowed_humor = 0.15
    if teacher_model.preferred_register in {"tapai", "hajur"}:
        allowed_humor = min(allowed_humor, 0.05)

    # Handle unresolved misunderstandings
    if session_memory.unresolved_misunderstandings:
        infer_vs_ask = "ask"
        confirmation_style = "repair"

    # Politeness level
    if teacher_model.preferred_register in {"hajur", "tapai"}:
        politeness_level = "high"
    elif teacher_model.preferred_register == "timi":
        politeness_level = "medium"
    else:
        politeness_level = "low"

    # Tone style
    tone_style = understanding.tone or "neutral"
    if understanding.is_correction:
        tone_style = "respectful_accepting"
    elif understanding.is_teaching:
        tone_style = "curious_warm"
    elif understanding.intent_label == "register_instruction":
        tone_style = "respectful_adjusting"
    elif understanding.intent_label == "pronunciation_guidance":
        tone_style = "careful_listening"

    dialect_alignment = understanding.dialect_guess or teacher_model.dialect_signature_hook or "neutral"

    # ─── Build and return policy ────────────────────────────────────────────
    return BehaviorPolicy(
        conversation_language=conversation_language,
        teach_language=teach_language,
        response_language=response_language,
        target_language_present=target_language_present,
        reply_mode=reply_mode,
        steer_to_target_language=steer_to_target,
        steering_strength=steering_strength,
        turn_goal=turn_goal,
        prompt_family=prompt_family,
        elicitation_goal=elicitation_goal,
        confirmation_goal=confirmation_goal,
        should_expand=should_expand,
        should_ask_followup=should_ask_followup,
        max_followups=1,
        handle_unclear_expression=handle_unclear,
        unclear_expression_strategy=unclear_strategy,
        mirror_code_switching=mirror_code_switching,
        register=teacher_model.preferred_register,
        tone_style=tone_style,
        uncertainty_level=round(uncertainty_level, 3),
        curiosity_level=round(curiosity_level, 3),
        confirmation_style=confirmation_style,
        allowed_humor=round(allowed_humor, 3),
        infer_vs_ask=infer_vs_ask,
        dialect_alignment=dialect_alignment,
        politeness_level=politeness_level,
        be_warm=reply_mode in {ReplyMode.FRIEND, ReplyMode.TEACH, ReplyMode.STUDENT},
        be_concise=True,
        act_slightly_unsure=reply_mode in {ReplyMode.STUDENT, ReplyMode.FRIEND},
        avoid_long_explanations=True,
        ask_at_most_one_question=should_ask_followup,
        treat_bridge_language_as_scaffolding=conversation_language in {"en", "ne", "mixed"},
        prioritize_target_language_elicitation=steer_to_target,
        confirm_before_expanding=should_expand,
        be_conversational_not_robotic=True,
    )
