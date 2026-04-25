from __future__ import annotations

import re


_DEVANAGARI_NUMBER_MAP = {
    "०": "शून्य",
    "१": "एक",
    "२": "दुई",
    "३": "तीन",
    "४": "चार",
    "५": "पाँच",
    "६": "छ",
    "७": "सात",
    "८": "आठ",
    "९": "नौ",
}
_ASCII_NUMBER_MAP = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}
_SYMBOL_MAP = {"&": " and ", "@": " at ", "%": " percent ", "+": " plus "}


def normalize_text_for_training(
    text: str,
    language_code: str,
    script: str,
    normalization_rules: list[str],
) -> dict:
    raw_text = str(text or "")
    normalized = raw_text
    normalization_type: list[str] = []
    warnings: list[str] = []

    if "normalize_numbers_to_spoken_form" in normalization_rules:
        updated = []
        changed = False
        number_map = _DEVANAGARI_NUMBER_MAP if script == "devanagari" else _ASCII_NUMBER_MAP
        for char in normalized:
            replacement = number_map.get(char)
            if replacement:
                updated.append(replacement)
                updated.append(" ")
                changed = True
            else:
                updated.append(char)
        if changed:
            normalized = "".join(updated)
            normalization_type.append("number_to_words")

    if "normalize_symbols_to_spoken_form" in normalization_rules:
        for symbol, replacement in _SYMBOL_MAP.items():
            if symbol in normalized:
                normalized = normalized.replace(symbol, replacement)
                if "symbol_to_words" not in normalization_type:
                    normalization_type.append("symbol_to_words")

    if "track_punctuation" in normalization_rules:
        collapsed = re.sub(r"\s+", " ", normalized).strip()
        if collapsed != normalized.strip():
            normalization_type.append("punctuation_spacing")
        normalized = collapsed

    if script == "devanagari":
        if "track_halant" in normalization_rules and ("्" in raw_text or "्" in normalized):
            normalization_type.append("halant_tracking")
        if "track_anusvara_chandrabindu" in normalization_rules and any(mark in raw_text + normalized for mark in ("ं", "ँ")):
            normalization_type.append("nasal_marker_tracking")
        if "track_word_boundaries" in normalization_rules and raw_text.replace(" ", "") != normalized.replace(" ", ""):
            warnings.append("word_boundary_changed")

    if not normalized:
        normalized = raw_text
        warnings.append("empty_normalization_fallback")

    return {
        "raw_text": raw_text,
        "normalized_text": normalized,
        "normalization_type": normalization_type,
        "warnings": warnings,
        "confidence": 0.95 if not warnings else 0.8,
        "language_code": language_code,
    }
