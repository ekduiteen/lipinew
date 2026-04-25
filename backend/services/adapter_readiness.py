from __future__ import annotations


def compute_adapter_readiness(
    *,
    country_code: str,
    target_language: str,
    gold_audio_hours: float,
    silver_audio_hours: float,
    gold_utterance_count: int,
    unique_teacher_count: int,
    speaker_diversity_score: float,
    dialect_diversity_score: float,
    correction_rate: float,
    drift_rate: float,
    dominant_error_type: str,
    domain_coverage_score: float,
) -> dict:
    if gold_audio_hours >= 200 and dialect_diversity_score >= 0.6:
        readiness_level = "dialect_adapter_ready"
    elif gold_audio_hours >= 50:
        readiness_level = "production_adapter_ready"
    elif gold_audio_hours >= 20:
        readiness_level = "benchmark_ready"
    elif gold_audio_hours >= 5:
        readiness_level = "experimental_adapter_ready"
    else:
        readiness_level = "collect_only"

    return {
        "country_code": country_code,
        "target_language": target_language,
        "gold_audio_hours": gold_audio_hours,
        "silver_audio_hours": silver_audio_hours,
        "gold_utterances": gold_utterance_count,
        "unique_teachers": unique_teacher_count,
        "speaker_diversity_score": speaker_diversity_score,
        "dialect_diversity_score": dialect_diversity_score,
        "correction_rate": correction_rate,
        "drift_rate": drift_rate,
        "dominant_error_type": dominant_error_type,
        "domain_coverage_score": domain_coverage_score,
        "readiness_level": readiness_level,
    }
