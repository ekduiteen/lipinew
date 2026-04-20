"""Session-aware keyterm preparation for STT biasing and extraction boosting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import logging
import re
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.intelligence import AdminKeytermSeed, ReviewQueueItem, VocabularyEntry, VocabularyTeacher
from models.user import User
from services.memory_service import StructuredSessionMemory

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]+")
_LATIN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_LANGUAGE_NAME_MAP = {
    "ne": "Nepali",
    "new": "Newari",
    "newari": "Newari",
    "mai": "Maithili",
    "en": "English",
}
_REGISTER_TERMS = (
    "तिमी",
    "तपाईं",
    "हजुर",
    "तँ",
    "timi",
    "tapai",
    "hajur",
    "ta",
)
logger = logging.getLogger("lipi.backend.keyterms")


def normalize_term(text: str) -> str:
    return " ".join(text.strip().lower().split())


@dataclass(frozen=True)
class KeytermCandidate:
    text: str
    normalized_text: str
    language: str
    source: str
    weight: float
    entity_type: str = "vocabulary"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class KeytermPreparation:
    candidates: list[KeytermCandidate] = field(default_factory=list)
    matched_from_session: list[str] = field(default_factory=list)
    matched_from_teacher_profile: list[str] = field(default_factory=list)
    matched_from_admin_seed: list[str] = field(default_factory=list)
    uncertain_candidates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "applied": [candidate.to_dict() for candidate in self.candidates],
            "matched_from_session": self.matched_from_session,
            "matched_from_teacher_profile": self.matched_from_teacher_profile,
            "matched_from_admin_seed": self.matched_from_admin_seed,
            "uncertain_candidates": self.uncertain_candidates,
            "prompt": self.prompt_hint,
        }

    @property
    def prompt_hint(self) -> str:
        if not self.candidates:
            return ""
        return ", ".join(candidate.text for candidate in self.candidates[:20])


def _extract_literal_terms(text: str) -> list[str]:
    raw_terms = _DEVANAGARI_RE.findall(text)
    raw_terms.extend(_LATIN_RE.findall(text))
    deduped: list[str] = []
    for term in raw_terms:
        normalized = normalize_term(term)
        if len(normalized) < 2 or normalized in deduped:
            continue
        deduped.append(normalized)
    return deduped


def _add_candidate(bucket: dict[str, KeytermCandidate], candidate: KeytermCandidate) -> None:
    existing = bucket.get(candidate.normalized_text)
    if existing is None or candidate.weight > existing.weight:
        bucket[candidate.normalized_text] = candidate


async def _load_teacher_history_keyterms(
    db: AsyncSession,
    *,
    teacher_id: str,
    limit: int,
) -> list[KeytermCandidate]:
    try:
        rows = (
            await db.execute(
                select(
                    VocabularyEntry.word,
                    VocabularyEntry.language,
                    func.count(VocabularyTeacher.id).label("support_count"),
                    func.max(VocabularyEntry.updated_at).label("latest_updated_at"),
                )
                .join(VocabularyTeacher, VocabularyTeacher.vocabulary_id == VocabularyEntry.id)
                .where(VocabularyTeacher.teacher_id == teacher_id)
                .group_by(VocabularyEntry.word, VocabularyEntry.language)
                .order_by(func.count(VocabularyTeacher.id).desc(), func.max(VocabularyEntry.updated_at).desc())
                .limit(limit)
            )
        ).all()
    except SQLAlchemyError as exc:
        logger.warning("Teacher history keyterms unavailable: %s", exc)
        return []
    return [
        KeytermCandidate(
            text=str(word),
            normalized_text=normalize_term(str(word)),
            language=str(language or "ne"),
            source="teacher_history",
            weight=min(0.7 + (int(count or 0) * 0.03), 0.95),
        )
        for word, language, count, _latest_updated_at in rows
    ]


async def _load_uncertain_keyterms(
    db: AsyncSession,
    *,
    teacher_id: str,
    limit: int = 5,
) -> list[str]:
    try:
        rows = (
            await db.execute(
                select(ReviewQueueItem.extracted_claim, func.count(ReviewQueueItem.id).label("hit_count"))
                .where(
                    ReviewQueueItem.teacher_id == teacher_id,
                    ReviewQueueItem.model_source == "learning_validation_guard",
                )
                .group_by(ReviewQueueItem.extracted_claim)
                .order_by(func.count(ReviewQueueItem.id).desc(), func.max(ReviewQueueItem.created_at).desc())
                .limit(limit)
            )
        ).all()
    except SQLAlchemyError as exc:
        logger.warning("Uncertain keyterms unavailable: %s", exc)
        return []
    return [str(claim) for claim, _ in rows if claim]


async def _load_admin_seed_keyterms(
    db: AsyncSession,
    *,
    language_keys: list[str],
    limit: int,
) -> list[KeytermCandidate]:
    normalized_keys = [key for key in dict.fromkeys(language_keys) if key]
    if not normalized_keys:
        normalized_keys = ["ne"]
    try:
        rows = (
            await db.execute(
                select(AdminKeytermSeed)
                .where(
                    AdminKeytermSeed.is_active.is_(True),
                    AdminKeytermSeed.language_key.in_(normalized_keys),
                )
                .order_by(AdminKeytermSeed.weight.desc(), AdminKeytermSeed.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
    except SQLAlchemyError as exc:
        logger.warning("Admin seed keyterms unavailable: %s", exc)
        return []
    return [
        KeytermCandidate(
            text=row.seed_text,
            normalized_text=row.normalized_text,
            language=row.language_key,
            source="admin_seed",
            weight=float(row.weight or 0.7),
            entity_type=row.entity_type,
        )
        for row in rows
    ]


async def prepare_turn_keyterms(
    db: AsyncSession,
    *,
    teacher_id: str,
    session_memory: dict,
    long_term_memory: StructuredSessionMemory | None = None,
    target_language: str | None = None,
) -> KeytermPreparation:
    if not settings.enable_keyterm_boosting:
        return KeytermPreparation()

    bucket: dict[str, KeytermCandidate] = {}
    source_matches: dict[str, list[str]] = defaultdict(list)
    uncertain_candidates = await _load_uncertain_keyterms(db, teacher_id=teacher_id)

    for term in (session_memory.get("taught_words") or [])[-settings.max_session_keyterms :]:
        normalized = normalize_term(str(term))
        if not normalized:
            continue
        candidate = KeytermCandidate(
            text=str(term),
            normalized_text=normalized,
            language=str(session_memory.get("active_language") or target_language or "ne"),
            source="session_memory",
            weight=0.95,
        )
        _add_candidate(bucket, candidate)
        source_matches["session_memory"].append(candidate.text)

    if session_memory.get("last_correction"):
        for term in _extract_literal_terms(str(session_memory["last_correction"])):
            candidate = KeytermCandidate(
                text=term,
                normalized_text=normalize_term(term),
                language=str(session_memory.get("active_language") or target_language or "ne"),
                source="session_memory",
                weight=0.98,
                entity_type="corrected_term",
            )
            _add_candidate(bucket, candidate)
            source_matches["session_memory"].append(candidate.text)

    if long_term_memory is not None:
        for term in long_term_memory.recent_taught_words[-settings.max_teacher_history_keyterms :]:
            normalized = normalize_term(str(term))
            if not normalized:
                continue
            candidate = KeytermCandidate(
                text=str(term),
                normalized_text=normalized,
                language=str(long_term_memory.active_language or target_language or "ne"),
                source="teacher_memory",
                weight=0.85,
            )
            _add_candidate(bucket, candidate)
            source_matches["teacher_history"].append(candidate.text)
        for correction in long_term_memory.recent_corrections[-4:]:
            for term in _extract_literal_terms(str(correction)):
                candidate = KeytermCandidate(
                    text=term,
                    normalized_text=normalize_term(term),
                    language=str(long_term_memory.active_language or target_language or "ne"),
                    source="teacher_memory",
                    weight=0.9,
                    entity_type="corrected_term",
                )
                _add_candidate(bucket, candidate)
                source_matches["teacher_history"].append(candidate.text)

    for term in _REGISTER_TERMS:
        candidate = KeytermCandidate(
            text=term,
            normalized_text=normalize_term(term),
            language="ne",
            source="admin_seed",
            weight=0.82,
            entity_type="honorific_or_register_term",
        )
        _add_candidate(bucket, candidate)
        source_matches["admin_seed"].append(candidate.text)

    active_language = str(
        (long_term_memory.active_language if long_term_memory else None)
        or session_memory.get("active_language")
        or target_language
        or "ne"
    ).lower()
    for lang_key in {active_language, str(target_language or "").lower(), "ne", "en", "new", "mai"}:
        display = _LANGUAGE_NAME_MAP.get(lang_key)
        if not display:
            continue
        for value in {display, display.lower(), lang_key}:
            candidate = KeytermCandidate(
                text=value,
                normalized_text=normalize_term(value),
                language="en" if value.isascii() else "ne",
                source="admin_seed",
                weight=0.8,
                entity_type="language_name",
            )
            _add_candidate(bucket, candidate)
            source_matches["admin_seed"].append(candidate.text)

    teacher_history = await _load_teacher_history_keyterms(
        db,
        teacher_id=teacher_id,
        limit=settings.max_teacher_history_keyterms,
    )
    for candidate in teacher_history:
        _add_candidate(bucket, candidate)
        source_matches["teacher_history"].append(candidate.text)

    admin_seed_candidates = await _load_admin_seed_keyterms(
        db,
        language_keys=[active_language, str(target_language or "").lower(), "ne", "en"],
        limit=settings.max_admin_seed_keyterms,
    )
    for candidate in admin_seed_candidates:
        _add_candidate(bucket, candidate)
        source_matches["admin_seed"].append(candidate.text)

    for term in uncertain_candidates:
        normalized = normalize_term(term)
        if not normalized:
            continue
        candidate = KeytermCandidate(
            text=term,
            normalized_text=normalized,
            language=active_language,
            source="uncertain_repeat",
            weight=0.72,
        )
        _add_candidate(bucket, candidate)

    ordered = sorted(bucket.values(), key=lambda candidate: (-candidate.weight, candidate.text))
    return KeytermPreparation(
        candidates=ordered[: max(settings.max_session_keyterms + settings.max_teacher_history_keyterms, 12)],
        matched_from_session=list(dict.fromkeys(source_matches["session_memory"]))[: settings.max_session_keyterms],
        matched_from_teacher_profile=list(dict.fromkeys(source_matches["teacher_history"]))[: settings.max_teacher_history_keyterms],
        matched_from_admin_seed=list(dict.fromkeys(source_matches["admin_seed"]))[: settings.max_admin_seed_keyterms],
        uncertain_candidates=uncertain_candidates,
    )


def match_candidates_in_text(text: str, preparation: KeytermPreparation) -> dict[str, list[str]]:
    normalized_text = normalize_term(text)
    matches = {
        "matched_from_session": [],
        "matched_from_teacher_profile": [],
        "matched_from_admin_seed": [],
        "applied": [],
    }
    for candidate in preparation.candidates:
        if candidate.normalized_text and candidate.normalized_text in normalized_text:
            matches["applied"].append(candidate.text)
            if candidate.text in preparation.matched_from_session:
                matches["matched_from_session"].append(candidate.text)
            if candidate.text in preparation.matched_from_teacher_profile:
                matches["matched_from_teacher_profile"].append(candidate.text)
            if candidate.text in preparation.matched_from_admin_seed:
                matches["matched_from_admin_seed"].append(candidate.text)
    for key in matches:
        matches[key] = list(dict.fromkeys(matches[key]))
    return matches


async def load_teacher_language_preferences(
    db: AsyncSession,
    *,
    teacher_id: str,
) -> list[str]:
    user = await db.get(User, teacher_id)
    if user is None:
        return []
    languages = [str(user.primary_language or "").strip()]
    languages.extend(str(language).strip() for language in (user.other_languages or []))
    return [language for language in dict.fromkeys(language.lower() for language in languages if language)]
