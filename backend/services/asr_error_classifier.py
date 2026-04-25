from __future__ import annotations

from collections import Counter


_FUNCTION_WORDS = {
    "ne": {"छ", "हो", "मा", "ले", "र", "लाई"},
    "newari": {"जा", "या", "गु", "नि"},
    "mai": {"छै", "के", "सँ", "मे"},
    "bho": {"बा", "के", "में", "से"},
}


def _space_only_difference(left: str, right: str) -> bool:
    return left.replace(" ", "") == right.replace(" ", "") and left != right


def _nasal_difference(left: str, right: str) -> bool:
    left_count = Counter(char for char in left if char in {"ं", "ँ"})
    right_count = Counter(char for char in right if char in {"ं", "ँ"})
    return left_count != right_count


def _halant_difference(left: str, right: str) -> bool:
    return left.count("्") != right.count("्")


def classify_asr_error(
    raw_stt: str,
    teacher_correction: str,
    language_profile: dict,
    script: str,
    drift_type: str,
) -> dict:
    raw = str(raw_stt or "")
    corrected = str(teacher_correction or "")
    taxonomy = set(language_profile.get("error_taxonomy", []))
    language_code = str(language_profile.get("language_code") or "").lower()

    if drift_type == "wrong_target_language":
        return {
            "error_type": "wrong_language_detection",
            "error_family": "language_routing",
            "severity": "high",
            "start_char": None,
            "end_char": None,
            "metadata": {"drift_type": drift_type},
        }
    if _space_only_difference(raw, corrected):
        return {
            "error_type": "word_boundary_error",
            "error_family": "segmentation",
            "severity": "medium",
            "start_char": None,
            "end_char": None,
            "metadata": {},
        }
    if script == "devanagari" and _halant_difference(raw, corrected):
        return {
            "error_type": "halant_cluster_error",
            "error_family": "orthography",
            "severity": "medium",
            "start_char": None,
            "end_char": None,
            "metadata": {},
        }
    if script == "devanagari" and _nasal_difference(raw, corrected):
        return {
            "error_type": "anusvara_chandrabindu_error",
            "error_family": "nasalization",
            "severity": "medium",
            "start_char": None,
            "end_char": None,
            "metadata": {},
        }

    function_words = _FUNCTION_WORDS.get(language_code, set())
    raw_tokens = raw.split()
    corrected_tokens = corrected.split()
    changed_tokens = [token for token in corrected_tokens if token not in raw_tokens]
    if changed_tokens and any(token in function_words for token in changed_tokens):
        return {
            "error_type": "function_word_particle_error",
            "error_family": "grammar_particle",
            "severity": "medium",
            "start_char": None,
            "end_char": None,
            "metadata": {},
        }
    if raw and corrected and abs(len(raw) - len(corrected)) <= max(3, len(corrected) // 4):
        return {
            "error_type": "lexical_substitution" if "lexical_substitution" in taxonomy else "unknown_error",
            "error_family": "lexical",
            "severity": "medium",
            "start_char": None,
            "end_char": None,
            "metadata": {},
        }
    return {
        "error_type": "unknown_error",
        "error_family": "unknown",
        "severity": "high",
        "start_char": None,
        "end_char": None,
        "metadata": {},
    }
