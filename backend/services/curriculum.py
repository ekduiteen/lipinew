"""Deterministic curriculum planner for per-user question selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.curriculum import (
    CurriculumPromptEvent,
    UserCurriculumProfile,
    UserTopicCoverage,
)
from models.user import User
from services.turn_interpreter import TurnInterpretation


@dataclass(frozen=True)
class TopicDefinition:
    topic_key: str
    display_name: str
    description: str
    example_question_intents: tuple[str, ...]
    allowed_question_types: tuple[str, ...]
    difficulty_level: int
    diversity_priority: bool


@dataclass(frozen=True)
class QuestionPlan:
    topic_key: str
    question_type: str
    register_key: str
    reason: str
    priority_score: float
    fallback_question_type: str
    assigned_lane: str
    language_key: str

    def to_prompt_block(self) -> str:
        return (
            "## Structured question plan\n"
            f"- Topic: {self.topic_key}\n"
            f"- Question type: {self.question_type}\n"
            f"- Register: {self.register_key}\n"
            f"- Language: {self.language_key}\n"
            f"- Assigned lane: {self.assigned_lane}\n"
            f"- Why this turn: {self.reason}\n"
            f"- Fallback question type: {self.fallback_question_type}\n"
            "- Reply in 2 short spoken sentences max\n"
            "- First react to the teacher's meaning\n"
            "- Then ask exactly one main question that matches the plan\n"
        )


QUESTION_TYPES: dict[str, str] = {
    "example_request": "Ask for one natural example sentence.",
    "contrast_request": "Ask for a contrast between two similar ways of saying something.",
    "casual_vs_formal": "Ask how the wording changes between casual and respectful speech.",
    "regional_variant": "Ask whether the wording changes by region or dialect.",
    "correction_check": "Offer a short attempt and invite correction.",
    "scenario_prompt": "Ask what people say in a specific everyday situation.",
    "how_would_you_say": "Ask how to say one concrete thing.",
    "what_do_friends_say": "Ask what friends usually say casually.",
    "what_do_elders_say": "Ask what elders or respectful speakers would say.",
    "when_is_this_used": "Ask when a word or phrase is actually used.",
}

TOPIC_TAXONOMY: dict[str, TopicDefinition] = {
    "everyday_basics": TopicDefinition(
        topic_key="everyday_basics",
        display_name="Everyday Basics",
        description="Greetings, common daily phrases, easy needs, and small talk.",
        example_question_intents=("greetings", "simple needs", "small talk"),
        allowed_question_types=("how_would_you_say", "example_request", "scenario_prompt"),
        difficulty_level=1,
        diversity_priority=False,
    ),
    "friendship_informal": TopicDefinition(
        "friendship_informal",
        "Friendship / Informal",
        "How friends talk casually, tease, invite, and check in.",
        ("friends chat", "hanging out", "casual talk"),
        ("what_do_friends_say", "casual_vs_formal", "scenario_prompt"),
        2,
        True,
    ),
    "family_home": TopicDefinition(
        "family_home",
        "Family / Home",
        "Home routines, relatives, chores, and family speech habits.",
        ("home routines", "family terms", "chores"),
        ("example_request", "scenario_prompt", "when_is_this_used"),
        2,
        False,
    ),
    "food_cooking": TopicDefinition(
        "food_cooking",
        "Food / Cooking",
        "Kitchen language, ingredients, preferences, and serving talk.",
        ("recipes", "ingredients", "meal preferences"),
        ("example_request", "scenario_prompt", "regional_variant"),
        2,
        False,
    ),
    "school_work": TopicDefinition(
        "school_work",
        "School / Work",
        "Teacher speech, student speech, workplace requests, and daily tasks.",
        ("classroom", "office tasks", "requests"),
        ("scenario_prompt", "casual_vs_formal", "example_request"),
        2,
        False,
    ),
    "instructions_requests": TopicDefinition(
        "instructions_requests",
        "Instructions / Requests",
        "How people ask, direct, remind, and request help.",
        ("requests", "directions", "reminders"),
        ("scenario_prompt", "casual_vs_formal", "what_do_elders_say"),
        2,
        True,
    ),
    "emotions_comfort": TopicDefinition(
        "emotions_comfort",
        "Emotions / Comfort",
        "How people show care, comfort, and emotional reactions.",
        ("comforting", "feelings", "check-ins"),
        ("example_request", "scenario_prompt", "when_is_this_used"),
        3,
        True,
    ),
    "conflict_scolding": TopicDefinition(
        "conflict_scolding",
        "Conflict / Scolding",
        "Disagreement, warning, scolding, and boundary-setting language.",
        ("scolding", "warning", "arguing"),
        ("scenario_prompt", "casual_vs_formal", "contrast_request"),
        4,
        True,
    ),
    "culture_ritual": TopicDefinition(
        "culture_ritual",
        "Culture / Ritual",
        "Festivals, rituals, blessings, greetings, and culturally-bound phrases.",
        ("ritual phrases", "festivals", "blessings"),
        ("when_is_this_used", "regional_variant", "example_request"),
        3,
        True,
    ),
    "regional_variation": TopicDefinition(
        "regional_variation",
        "Regional Variation",
        "Dialect differences, local word choices, and region-specific phrasing.",
        ("dialect differences", "local variants", "region-specific words"),
        ("regional_variant", "contrast_request", "what_do_friends_say"),
        4,
        True,
    ),
    "story_memory": TopicDefinition(
        "story_memory",
        "Story / Memory",
        "Narratives, memories, anecdotes, and remembered expressions.",
        ("memories", "storytelling", "anecdotes"),
        ("scenario_prompt", "example_request", "when_is_this_used"),
        3,
        True,
    ),
    "humor_playfulness": TopicDefinition(
        "humor_playfulness",
        "Humor / Playfulness",
        "Jokes, teasing, affectionate playfulness, and light banter.",
        ("jokes", "playful talk", "light teasing"),
        ("what_do_friends_say", "contrast_request", "scenario_prompt"),
        4,
        True,
    ),
}

LANE_TOPICS: dict[str, tuple[str, ...]] = {
    "basics_lane": ("everyday_basics", "instructions_requests", "family_home"),
    "social_lane": ("friendship_informal", "emotions_comfort", "humor_playfulness"),
    "formal_lane": ("culture_ritual", "school_work", "instructions_requests"),
    "regional_lane": ("regional_variation", "culture_ritual", "story_memory"),
    "correction_lane": ("instructions_requests", "friendship_informal", "regional_variation"),
}


def infer_language_key(teacher_text: str, detected_language: str | None) -> str:
    lowered = (detected_language or "").lower()
    if lowered:
        return lowered
    if any(token in teacher_text.lower() for token in ("newari", "nepal bhasa", "newa")):
        return "new"
    if any(ch.isascii() and ch.isalpha() for ch in teacher_text):
        return "en"
    return "ne"


def _detect_topic_hints(text: str) -> set[str]:
    lowered = text.lower()
    topic_hits: set[str] = set()
    if any(word in lowered for word in ("friend", "sathi", "saathi", "साथी", "hangout", "joke", "fun")):
        topic_hits.add("friendship_informal")
    if any(word in lowered for word in ("ama", "baba", "घर", "family", "kitchen", "home")):
        topic_hits.add("family_home")
    if any(word in lowered for word in ("food", "cook", "rice", "dal", "खाना", "भान्सा")):
        topic_hits.add("food_cooking")
    if any(word in lowered for word in ("school", "class", "office", "work", "homework", "teacher")):
        topic_hits.add("school_work")
    if any(word in lowered for word in ("please", "request", "help", "bring", "लिनु", "दिनु", "can you")):
        topic_hits.add("instructions_requests")
    if any(word in lowered for word in ("happy", "sad", "feel", "खुसी", "दुख", "comfort")):
        topic_hits.add("emotions_comfort")
    if any(word in lowered for word in ("angry", "scold", "fight", "कर", "गाली", "झगडा")):
        topic_hits.add("conflict_scolding")
    if any(word in lowered for word in ("festival", "ritual", "dashain", "tihar", "blessing", "पूजा")):
        topic_hits.add("culture_ritual")
    if any(word in lowered for word in ("newari", "maithili", "bhojpuri", "region", "dialect", "accent", "local")):
        topic_hits.add("regional_variation")
    if any(word in lowered for word in ("story", "memory", "once", "childhood", "कथा", "याद")):
        topic_hits.add("story_memory")
    if any(word in lowered for word in ("funny", "tease", "joke", "हासो", "मजाक")):
        topic_hits.add("humor_playfulness")
    if not topic_hits:
        topic_hits.add("everyday_basics")
    return topic_hits


def detect_question_type_from_context(teacher_text: str, corrected: bool) -> str:
    lowered = teacher_text.lower()
    if corrected:
        return "correction_check"
    if any(token in lowered for token in ("difference", "different", "vs", "भन्दा", "फरक")):
        return "contrast_request"
    if any(token in lowered for token in ("friend", "sathi", "साथी")):
        return "what_do_friends_say"
    if any(token in lowered for token in ("elder", "respect", "hajur", "तपाईं", "elders")):
        return "what_do_elders_say"
    if any(token in lowered for token in ("when", "used", "कहिले", "प्रयोग")):
        return "when_is_this_used"
    return "scenario_prompt"


def assign_lane(
    user: User,
    profile: UserCurriculumProfile,
    memory: dict,
    corrected_recently: bool,
) -> str:
    if corrected_recently or profile.correction_count >= 3:
        return "correction_lane"
    if any(lang in ("new", "mai", "bho", "tharu") for lang in [memory.get("active_language")]):
        return "regional_lane"
    if (user.age or 0) >= 45 or profile.active_register in {"tapai", "hajur"}:
        return "formal_lane"
    if profile.comfort_level >= 0.65 or profile.code_switch_tendency >= 0.45:
        return "social_lane"
    return "basics_lane"


async def get_or_create_user_profile(
    db: AsyncSession,
    user: User,
    *,
    active_register: str,
    code_switch_tendency: float,
) -> UserCurriculumProfile:
    profile = await db.get(UserCurriculumProfile, user.id)
    if profile:
        return profile

    profile = UserCurriculumProfile(
        user_id=user.id,
        primary_language=(user.primary_language or "ne")[:16],
        active_register=active_register,
        code_switch_tendency=code_switch_tendency,
        comfort_level=0.5,
        assigned_lane="basics_lane",
    )
    db.add(profile)
    await db.flush()
    return profile


async def get_recent_question_types(
    db: AsyncSession,
    user_id: str,
    *,
    limit: int = 5,
) -> list[str]:
    rows = await db.execute(
        select(CurriculumPromptEvent.question_type)
        .where(CurriculumPromptEvent.user_id == user_id)
        .order_by(desc(CurriculumPromptEvent.created_at))
        .limit(limit)
    )
    return [question_type for (question_type,) in rows]


async def get_recent_topics(
    db: AsyncSession,
    user_id: str,
    *,
    limit: int = 5,
) -> list[str]:
    rows = await db.execute(
        select(CurriculumPromptEvent.topic_key)
        .where(CurriculumPromptEvent.user_id == user_id)
        .order_by(desc(CurriculumPromptEvent.created_at))
        .limit(limit)
    )
    return [topic_key for (topic_key,) in rows]


def _topic_priority(
    topic_key: str,
    *,
    lane: str,
    hinted_topics: set[str],
    recent_topics: list[str],
    gap_score: float,
    corrected_recently: bool,
) -> float:
    score = 0.4 + gap_score
    if topic_key in hinted_topics:
        score += 0.9
    if topic_key in LANE_TOPICS.get(lane, ()):
        score += 0.55
    if topic_key in recent_topics[:2]:
        score -= 0.55
    elif topic_key in recent_topics:
        score -= 0.2
    topic = TOPIC_TAXONOMY[topic_key]
    if topic.diversity_priority:
        score += 0.25
    if corrected_recently and topic_key in {"regional_variation", "instructions_requests", "friendship_informal"}:
        score += 0.35
    return score


def _pick_question_type(
    topic_key: str,
    recent_question_types: list[str],
    lane: str,
    corrected_recently: bool,
) -> tuple[str, str]:
    allowed = list(TOPIC_TAXONOMY[topic_key].allowed_question_types)
    if corrected_recently and "correction_check" in QUESTION_TYPES and "correction_check" not in allowed:
        allowed.insert(0, "correction_check")
    if lane == "regional_lane" and "regional_variant" in allowed:
        preferred = "regional_variant"
    elif lane == "formal_lane" and "what_do_elders_say" in allowed:
        preferred = "what_do_elders_say"
    elif lane == "social_lane" and "what_do_friends_say" in allowed:
        preferred = "what_do_friends_say"
    elif lane == "correction_lane" and "contrast_request" in allowed:
        preferred = "contrast_request"
    else:
        preferred = allowed[0]

    for candidate in [preferred, *allowed]:
        if candidate not in recent_question_types[:2]:
            fallback = next((item for item in allowed if item != candidate), candidate)
            return candidate, fallback
    return allowed[0], allowed[min(1, len(allowed) - 1)]


def _calculate_comfort_level(profile: UserCurriculumProfile, memory: dict) -> float:
    base = 0.45
    base += min(profile.conversation_turn_count, 12) * 0.02
    base += min(profile.correction_count, 6) * 0.03
    if memory.get("teacher_intent") in {"story", "feeling"}:
        base += 0.08
    return max(0.2, min(base, 0.95))


def detect_correction_signal(text: str) -> bool:
    lowered = text.lower()
    correction_markers = (
        "होइन",
        "भन्ने होइन",
        "not like that",
        "say it like",
        "correct is",
        "यसरी भन्नु",
        "यसरी भनिन्छ",
        "instead",
    )
    return any(marker in lowered for marker in correction_markers)


def estimate_response_quality(text: str, stt_confidence: float | None) -> float:
    confidence = float(stt_confidence or 0.0)
    length_bonus = 0.15 if 8 <= len(text.strip()) <= 140 else 0.0
    return round(max(0.0, min(confidence + length_bonus, 1.0)), 3)


async def plan_next_question(
    db: AsyncSession,
    *,
    user: User,
    user_profile: UserCurriculumProfile,
    session_state: dict,
    turn_interpretation: TurnInterpretation,
    register_key: str,
    gap_scores: dict[tuple[str, str, str], float],
    corrected_recently: bool,
) -> QuestionPlan:
    recent_turn = session_state.get("latest_teacher_text") or ""
    language_key = infer_language_key(recent_turn, session_state.get("active_language"))
    lane = assign_lane(user, user_profile, session_state, corrected_recently)
    hinted_topics = _detect_topic_hints(recent_turn)
    if turn_interpretation.active_topic:
        hinted_topics.add(turn_interpretation.active_topic)
    recent_question_types = await get_recent_question_types(db, user.id)
    recent_topics = await get_recent_topics(db, user.id)

    best_topic = "everyday_basics"
    best_score = -999.0
    for topic_key in TOPIC_TAXONOMY:
        gap_score = gap_scores.get((topic_key, register_key, language_key), 0.65)
        score = _topic_priority(
            topic_key,
            lane=lane,
            hinted_topics=hinted_topics,
            recent_topics=recent_topics,
            gap_score=gap_score,
            corrected_recently=corrected_recently,
        )
        if score > best_score:
            best_topic = topic_key
            best_score = score

    question_type, fallback_question_type = _pick_question_type(
        best_topic,
        recent_question_types,
        lane,
        corrected_recently,
    )

    if corrected_recently or turn_interpretation.is_correction:
        reason = "Teacher just corrected LIPI; bias toward contrast/correction-rich follow-up."
    elif best_topic in hinted_topics:
        reason = "Teacher's latest turn strongly hinted this topic and it still has useful coverage value."
    elif lane == "regional_lane":
        reason = "User fits a regional diversity lane and this topic is under-collected."
    else:
        reason = "Balance current relevance, user lane, and global coverage gap while avoiding repetition."

    return QuestionPlan(
        topic_key=best_topic,
        question_type=question_type,
        register_key=register_key,
        reason=reason,
        priority_score=round(best_score, 3),
        fallback_question_type=fallback_question_type,
        assigned_lane=lane,
        language_key=language_key,
    )


async def sync_profile_after_plan(
    db: AsyncSession,
    profile: UserCurriculumProfile,
    plan: QuestionPlan,
    *,
    corrected_recently: bool,
) -> None:
    profile.active_register = plan.register_key
    profile.assigned_lane = plan.assigned_lane
    profile.last_topic = plan.topic_key
    profile.last_question_type = plan.question_type
    profile.comfort_level = _calculate_comfort_level(profile, {"teacher_intent": None})
    if corrected_recently:
        profile.correction_count += 1
    profile.last_updated_at = datetime.now(timezone.utc)
    await db.flush()


async def get_or_create_topic_coverage(
    db: AsyncSession,
    *,
    user_id: str,
    topic_key: str,
) -> UserTopicCoverage:
    row = await db.execute(
        select(UserTopicCoverage)
        .where(UserTopicCoverage.user_id == user_id, UserTopicCoverage.topic_key == topic_key)
        .limit(1)
    )
    coverage = row.scalar_one_or_none()
    if coverage:
        return coverage

    coverage = UserTopicCoverage(
        id=str(uuid.uuid4()),
        user_id=user_id,
        topic_key=topic_key,
    )
    db.add(coverage)
    await db.flush()
    return coverage


async def record_prompt_event(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    plan: QuestionPlan,
) -> CurriculumPromptEvent:
    event = CurriculumPromptEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=session_id,
        topic_key=plan.topic_key,
        question_type=plan.question_type,
        register_key=plan.register_key,
        language_key=plan.language_key,
        assigned_lane=plan.assigned_lane,
        reason=plan.reason,
        priority_score=plan.priority_score,
        fallback_question_type=plan.fallback_question_type,
    )
    db.add(event)

    coverage = await get_or_create_topic_coverage(db, user_id=user_id, topic_key=plan.topic_key)
    coverage.times_asked += 1
    coverage.last_seen_at = datetime.now(timezone.utc)

    return event


async def resolve_latest_prompt_event(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: str,
    teacher_text: str,
    stt_confidence: float | None,
) -> CurriculumPromptEvent | None:
    row = await db.execute(
        select(CurriculumPromptEvent)
        .where(
            CurriculumPromptEvent.user_id == user_id,
            CurriculumPromptEvent.session_id == session_id,
            CurriculumPromptEvent.was_answered.is_(False),
        )
        .order_by(desc(CurriculumPromptEvent.created_at))
        .limit(1)
    )
    event = row.scalar_one_or_none()
    if event is None:
        return None

    event.was_answered = True
    event.was_corrected = detect_correction_signal(teacher_text)
    event.response_quality = estimate_response_quality(teacher_text, stt_confidence)
    event.answered_at = datetime.now(timezone.utc)

    return event


def plan_examples() -> dict[str, dict]:
    return {
        "new_user": asdict(
            QuestionPlan(
                topic_key="everyday_basics",
                question_type="how_would_you_say",
                register_key="tapai",
                reason="New user with low turn count starts in basics lane with a concrete phrase prompt.",
                priority_score=1.42,
                fallback_question_type="example_request",
                assigned_lane="basics_lane",
                language_key="ne",
            )
        ),
        "informal_social_user": asdict(
            QuestionPlan(
                topic_key="friendship_informal",
                question_type="what_do_friends_say",
                register_key="timi",
                reason="High comfort and expressive tone push this user toward socially rich casual data.",
                priority_score=1.88,
                fallback_question_type="casual_vs_formal",
                assigned_lane="social_lane",
                language_key="ne",
            )
        ),
        "regional_gap_case": asdict(
            QuestionPlan(
                topic_key="regional_variation",
                question_type="regional_variant",
                register_key="tapai",
                reason="Regional variation is under-collected for this register/language pair.",
                priority_score=2.04,
                fallback_question_type="contrast_request",
                assigned_lane="regional_lane",
                language_key="new",
            )
        ),
        "correction_heavy_user": asdict(
            QuestionPlan(
                topic_key="instructions_requests",
                question_type="contrast_request",
                register_key="timi",
                reason="Frequent corrections make contrast-heavy prompts more valuable than open-ended basics.",
                priority_score=1.97,
                fallback_question_type="correction_check",
                assigned_lane="correction_lane",
                language_key="ne",
            )
        ),
    }
