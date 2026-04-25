from __future__ import annotations

from services.language_registry import load_language_profile


def detect_asr_drift(
    target_language: str,
    selected_language: str,
    detected_language: str,
    base_asr_languages: list[str],
    confidence: float,
    code_switch_ratio: float,
    candidates: list[dict],
) -> dict:
    del candidates

    target = str(target_language or "").lower()
    selected = str(selected_language or "").lower()
    detected = str(detected_language or "").lower()
    base = {str(item).lower() for item in (base_asr_languages or [])}

    try:
        profile = load_language_profile(target)
        thresholds = profile.get("quality_thresholds", {})
    except ValueError:
        thresholds = {}

    low_confidence_threshold = float(thresholds.get("low_confidence", 0.55))
    code_switch_threshold = 0.3

    if confidence < low_confidence_threshold:
        return {
            "asr_drift_type": "low_confidence",
            "needs_teacher_confirmation": True,
            "reason": f"confidence_below_threshold:{confidence:.2f}<{low_confidence_threshold:.2f}",
            "severity": "high",
        }
    if code_switch_ratio > code_switch_threshold:
        return {
            "asr_drift_type": "code_switch_detected",
            "needs_teacher_confirmation": True,
            "reason": f"code_switch_ratio={code_switch_ratio:.2f}",
            "severity": "medium",
        }
    if not selected:
        return {
            "asr_drift_type": "unknown_language",
            "needs_teacher_confirmation": True,
            "reason": "selected_language_missing",
            "severity": "high",
        }
    if selected == "en" and target != "en":
        return {
            "asr_drift_type": "english_drift",
            "needs_teacher_confirmation": True,
            "reason": "english_selected_for_non_english_target",
            "severity": "high",
        }
    if target and selected != target and selected in base:
        return {
            "asr_drift_type": "base_language_drift",
            "needs_teacher_confirmation": True,
            "reason": f"selected_base_language={selected}",
            "severity": "medium",
        }
    if target and selected not in base and selected != target:
        return {
            "asr_drift_type": "wrong_target_language",
            "needs_teacher_confirmation": True,
            "reason": f"selected_language={selected}",
            "severity": "high",
        }
    if detected and detected not in base and detected != target and detected != selected:
        return {
            "asr_drift_type": "unknown_language",
            "needs_teacher_confirmation": True,
            "reason": f"detected_language={detected}",
            "severity": "high",
        }
    if target and selected == target and detected and detected != target and detected in base:
        return {
            "asr_drift_type": "target_language_uncertain",
            "needs_teacher_confirmation": True,
            "reason": f"detected={detected}, selected={selected}",
            "severity": "medium",
        }
    return {
        "asr_drift_type": "no_drift",
        "needs_teacher_confirmation": False,
        "reason": "target_consistent",
        "severity": "low",
    }
