from __future__ import annotations

from typing import Optional


def assign_training_tier(
    audio_quality: float,
    stt_confidence: float,
    teacher_verified: bool,
    teacher_corrected: bool,
    consent_training_use: bool,
    asr_drift_type: str,
    error_type: Optional[str],
    language_profile: dict,
) -> dict:
    thresholds = language_profile.get("quality_thresholds", {})
    gold_audio_quality = float(thresholds.get("gold_audio_quality", 0.85))
    silver_audio_quality = float(thresholds.get("silver_audio_quality", 0.7))
    high_confidence = float(thresholds.get("high_confidence", 0.8))

    if not consent_training_use:
        return {"training_tier": "rejected", "training_eligible": False, "reason": "no_consent"}
    if asr_drift_type == "wrong_target_language" and not teacher_corrected:
        return {"training_tier": "rejected", "training_eligible": False, "reason": "wrong_language_uncorrected"}
    if audio_quality < 0.3:
        return {"training_tier": "rejected", "training_eligible": False, "reason": "poor_audio_quality"}
    if teacher_corrected and teacher_verified and audio_quality >= gold_audio_quality and error_type != "noise_overlap_error":
        return {"training_tier": "gold", "training_eligible": True, "reason": "teacher_corrected_clean_audio"}
    if teacher_verified and not teacher_corrected and audio_quality >= silver_audio_quality and stt_confidence >= high_confidence and asr_drift_type == "no_drift":
        return {"training_tier": "silver", "training_eligible": True, "reason": "teacher_verified_high_confidence"}
    if teacher_verified or stt_confidence > 0.0:
        return {"training_tier": "bronze", "training_eligible": False, "reason": "archive_only"}
    return {"training_tier": "rejected", "training_eligible": False, "reason": "unusable"}
