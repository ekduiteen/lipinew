"""Transcript repair using high-confidence keyterm context."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
import re

from config import settings
from services.keyterm_service import KeytermPreparation, normalize_term

_TOKEN_RE = re.compile(r"[\u0900-\u097F]+|[A-Za-z]+(?:'[A-Za-z]+)?|\S")


def _soft_normalize(value: str) -> str:
    normalized = normalize_term(value)
    for marker in ("ं", "ँ"):
        normalized = normalized.replace(marker, "")
    return normalized


@dataclass(frozen=True)
class TranscriptRepairResult:
    original_text: str
    repaired_text: str
    applied_repairs: list[dict] = field(default_factory=list)
    uncertain_candidates: list[str] = field(default_factory=list)
    confidence_after: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _is_safe_substitution(original: str, candidate: str) -> bool:
    if original == candidate:
        return False
    if original in candidate and len(candidate) - len(original) <= 1:
        return True
    if _soft_normalize(original) == _soft_normalize(candidate):
        return True
    return False


def repair_transcript(
    *,
    transcript: str,
    stt_confidence: float,
    keyterms: KeytermPreparation,
) -> TranscriptRepairResult:
    if not settings.transcript_repair_enabled or not transcript.strip():
        return TranscriptRepairResult(
            original_text=transcript,
            repaired_text=transcript,
            uncertain_candidates=keyterms.uncertain_candidates,
            confidence_after=stt_confidence,
        )

    if stt_confidence >= settings.transcript_repair_min_confidence:
        return TranscriptRepairResult(
            original_text=transcript,
            repaired_text=transcript,
            uncertain_candidates=keyterms.uncertain_candidates,
            confidence_after=stt_confidence,
        )

    tokens = _TOKEN_RE.findall(transcript)
    if not tokens:
        return TranscriptRepairResult(
            original_text=transcript,
            repaired_text=transcript,
            uncertain_candidates=keyterms.uncertain_candidates,
            confidence_after=stt_confidence,
        )

    applied_repairs: list[dict] = []
    repaired_tokens: list[str] = []
    keyterm_map = {candidate.normalized_text: candidate for candidate in keyterms.candidates}

    for token in tokens:
        normalized = normalize_term(token)
        repaired = token
        if normalized and normalized not in keyterm_map:
            best_candidate = None
            best_similarity = 0.0
            for candidate in keyterms.candidates:
                if abs(len(candidate.normalized_text) - len(normalized)) > 2:
                    continue
                similarity = max(
                    _similarity(normalized, candidate.normalized_text),
                    _similarity(_soft_normalize(normalized), _soft_normalize(candidate.normalized_text)),
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_candidate = candidate
            if (
                best_candidate is not None
                and best_similarity >= (0.78 if re.search(r"[\u0900-\u097F]", normalized) else 0.88)
                and best_candidate.weight >= 0.8
                and _is_safe_substitution(normalized, best_candidate.normalized_text)
            ):
                repaired = best_candidate.text
                applied_repairs.append(
                    {
                        "from": token,
                        "to": repaired,
                        "similarity": round(best_similarity, 3),
                        "source": best_candidate.source,
                    }
                )
        repaired_tokens.append(repaired)

    repaired_text = " ".join(repaired_tokens)
    repaired_text = repaired_text.replace(" ।", "।").replace(" ?", "?").replace(" ,", ",")
    confidence_after = min(
        0.99,
        stt_confidence + (0.04 * len(applied_repairs)),
    )
    return TranscriptRepairResult(
        original_text=transcript,
        repaired_text=repaired_text,
        applied_repairs=applied_repairs,
        uncertain_candidates=keyterms.uncertain_candidates,
        confidence_after=confidence_after,
    )
