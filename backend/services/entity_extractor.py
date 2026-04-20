"""Structured entity extraction for teacher turns."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re

from config import settings
from services.intent_classifier import IntentResult
from services.keyterm_service import KeytermPreparation, normalize_term

_TOKEN_RE = re.compile(r"[\u0900-\u097F]+(?:\s+[\u0900-\u097F]+)*|[A-Za-z]+(?:['-][A-Za-z]+)?(?:\s+[A-Za-z]+(?:['-][A-Za-z]+)?)?")
_LANGUAGE_TOKENS = {
    "nepali": "en",
    "english": "en",
    "newari": "en",
    "newar": "en",
    "maithili": "en",
    "नेपाली": "ne",
    "अंग्रेजी": "ne",
    "नेवारी": "ne",
    "नेपाल भाषा": "ne",
    "मैथिली": "ne",
}
_REGISTER_TOKENS = {"तिमी", "तपाईं", "हजुर", "तँ", "timi", "tapai", "hajur", "ta"}
_STOPWORDS = {"हो", "छ", "र", "the", "and", "this", "that", "is", "are"}


@dataclass(frozen=True)
class ExtractedEntity:
    text: str
    normalized_text: str
    entity_type: str
    language: str | None
    confidence: float
    source_span: tuple[int | None, int | None]
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["source_span"] = list(self.source_span)
        return payload


def _span_for(text: str, needle: str) -> tuple[int | None, int | None]:
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return None, None
    return idx, idx + len(needle)


def _guess_language(value: str) -> str | None:
    if re.search(r"[\u0900-\u097F]", value):
        return "ne"
    if re.search(r"[A-Za-z]", value):
        return "en"
    return None


def _dedupe(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    bucket: dict[tuple[str, str], ExtractedEntity] = {}
    for entity in entities:
        key = (entity.entity_type, entity.normalized_text)
        existing = bucket.get(key)
        if existing is None or entity.confidence > existing.confidence:
            bucket[key] = entity
    return list(bucket.values())


def extract_entities(
    *,
    text: str,
    intent: IntentResult,
    keyterms: KeytermPreparation,
    primary_language: str | None,
) -> list[ExtractedEntity]:
    if not settings.enable_entity_extraction:
        return []

    entities: list[ExtractedEntity] = []
    lowered = text.lower()

    for candidate in keyterms.candidates:
        if candidate.normalized_text in normalize_term(text):
            entity_type = candidate.entity_type
            confidence = min(0.7 + (candidate.weight * 0.25), 0.98)
            entities.append(
                ExtractedEntity(
                    text=candidate.text,
                    normalized_text=candidate.normalized_text,
                    entity_type=entity_type,
                    language=candidate.language,
                    confidence=round(confidence, 3),
                    source_span=_span_for(text, candidate.text),
                    attributes={
                        "is_keyterm": True,
                        "source": candidate.source,
                        "register": candidate.text if entity_type == "honorific_or_register_term" else None,
                    },
                )
            )

    if " means " in lowered or " भनेको " in text:
        if " means " in lowered:
            left, right = text.split(" means ", 1)
        else:
            left, right = text.split("भनेको", 1)
        left_terms = [token for token in _TOKEN_RE.findall(left) if normalize_term(token) not in _STOPWORDS]
        right_terms = [token for token in _TOKEN_RE.findall(right) if normalize_term(token) not in _STOPWORDS]
        if left_terms:
            taught = left_terms[-1].strip()
            entities.append(
                ExtractedEntity(
                    text=taught,
                    normalized_text=normalize_term(taught),
                    entity_type="vocabulary" if len(taught.split()) == 1 else "phrase",
                    language=_guess_language(taught) or primary_language,
                    confidence=0.88,
                    source_span=_span_for(text, taught),
                    attributes={"is_keyterm": normalize_term(taught) in {candidate.normalized_text for candidate in keyterms.candidates}},
                )
            )
        if right_terms:
            gloss = " ".join(right_terms[:4]).strip()
            entities.append(
                ExtractedEntity(
                    text=gloss,
                    normalized_text=normalize_term(gloss),
                    entity_type="gloss_or_meaning",
                    language=_guess_language(gloss),
                    confidence=0.82,
                    source_span=_span_for(text, gloss),
                    attributes={"relation": "meaning_of_previous_term"},
                )
            )

    if intent.label == "correction":
        correction_terms = [token for token in _TOKEN_RE.findall(text) if normalize_term(token) not in _STOPWORDS]
        if correction_terms:
            corrected = correction_terms[-1].strip()
            entities.append(
                ExtractedEntity(
                    text=corrected,
                    normalized_text=normalize_term(corrected),
                    entity_type="corrected_term",
                    language=_guess_language(corrected) or primary_language,
                    confidence=0.84,
                    source_span=_span_for(text, corrected),
                    attributes={"is_corrected_term": True},
                )
            )

    if intent.label == "pronunciation_guidance":
        terms = [token for token in _TOKEN_RE.findall(text) if normalize_term(token) not in _STOPWORDS]
        if terms:
            target = terms[-1]
            entities.append(
                ExtractedEntity(
                    text=target,
                    normalized_text=normalize_term(target),
                    entity_type="pronunciation_target",
                    language=_guess_language(target) or primary_language,
                    confidence=0.87,
                    source_span=_span_for(text, target),
                    attributes={"pronunciation_focus": True},
                )
            )

    if intent.label == "example":
        entities.append(
            ExtractedEntity(
                text=text,
                normalized_text=normalize_term(text),
                entity_type="example_usage",
                language=primary_language,
                confidence=0.72,
                source_span=(0, len(text)),
                attributes={"full_sentence": True},
            )
        )

    for token, lang in _LANGUAGE_TOKENS.items():
        if token in lowered:
            entities.append(
                ExtractedEntity(
                    text=token,
                    normalized_text=normalize_term(token),
                    entity_type="language_name",
                    language=lang,
                    confidence=0.9,
                    source_span=_span_for(text, token),
                    attributes={"language_name": token},
                )
            )

    for token in _REGISTER_TOKENS:
        if token.lower() in lowered:
            entities.append(
                ExtractedEntity(
                    text=token,
                    normalized_text=normalize_term(token),
                    entity_type="honorific_or_register_term",
                    language=_guess_language(token) or primary_language,
                    confidence=0.91,
                    source_span=_span_for(text, token),
                    attributes={"register": normalize_term(token)},
                )
            )

    if any(term in lowered for term in ("culture", "tradition", "respect", "संस्कृति", "सम्मान")):
        entities.append(
            ExtractedEntity(
                text=text,
                normalized_text=normalize_term(text),
                entity_type="cultural_concept",
                language=primary_language,
                confidence=0.65,
                source_span=(0, len(text)),
                attributes={"contextual": True},
            )
        )

    tokens = [token.strip() for token in _TOKEN_RE.findall(text)]
    for token in tokens[:8]:
        normalized = normalize_term(token)
        if len(normalized) < 2 or normalized in _STOPWORDS:
            continue
        if any(entity.normalized_text == normalized for entity in entities):
            continue
        entity_type = "vocabulary"
        if len(token.split()) > 1:
            entity_type = "phrase"
        elif token[:1].isupper() and re.search(r"[A-Za-z]", token):
            entity_type = "proper_name"
        entities.append(
            ExtractedEntity(
                text=token,
                normalized_text=normalized,
                entity_type=entity_type,
                language=_guess_language(token) or primary_language,
                confidence=0.58 if entity_type == "vocabulary" else 0.62,
                source_span=_span_for(text, token),
                attributes={"is_keyterm": False},
            )
        )

    return _dedupe(entities)
