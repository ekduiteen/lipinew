from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

from models.message import Message
from models.session import TeachingSession
from models.user import User
from services.asr_drift import detect_asr_drift
from services.asr_error_classifier import classify_asr_error
from services.country_registry import get_base_asr_languages, load_country_profile, validate_country_target_language
from services.data_quality import assign_training_tier
from services.language_registry import get_language_inheritance_chain, load_language_profile
from services.text_normalization import normalize_text_for_training
from services.adapter_readiness import compute_adapter_readiness


def test_country_registry_loads_nepal_and_rejects_unsupported_language():
    profile = load_country_profile("NP")

    assert profile["country_name"] == "Nepal"
    assert get_base_asr_languages("NP") == ["ne", "en"]
    assert validate_country_target_language("NP", "newari") is True
    assert validate_country_target_language("NP", "klingon") is False


def test_language_registry_loads_newari_maithili_and_inheritance():
    newari = load_language_profile("newari")
    maithili = load_language_profile("mai")

    assert newari["display_name"] == "Nepal Bhasha / Newari"
    assert maithili["display_name"] == "Maithili"
    assert get_language_inheritance_chain("mai") == ["mai", "ne", "hi", "en"]


def test_asr_drift_rules():
    assert detect_asr_drift("newari", "ne", "ne", ["ne", "en"], 0.8, 0.0, [])["asr_drift_type"] == "base_language_drift"
    assert detect_asr_drift("taj", "en", "en", ["ne", "en"], 0.8, 0.0, [])["asr_drift_type"] == "english_drift"
    assert detect_asr_drift("newari", "newari", "ne", ["ne", "en"], 0.1, 0.0, [])["asr_drift_type"] == "low_confidence"


def test_text_normalization_preserves_original_and_tracks_devanagari_markers():
    result = normalize_text_for_training(
        "१२ आँखा",
        language_code="newari",
        script="devanagari",
        normalization_rules=["preserve_original", "normalize_numbers_to_spoken_form", "track_anusvara_chandrabindu", "track_halant"],
    )

    assert result["raw_text"] == "१२ आँखा"
    assert result["normalized_text"] != ""
    assert "number_to_words" in result["normalization_type"]
    assert "nasal_marker_tracking" in result["normalization_type"]


def test_asr_error_classifier_rules():
    profile = load_language_profile("newari")

    assert classify_asr_error("नेपालभाषा", "नेपाल भाषा", profile, "devanagari", "no_drift")["error_type"] == "word_boundary_error"
    assert classify_asr_error("आखा", "आँखा", profile, "devanagari", "no_drift")["error_type"] == "anusvara_chandrabindu_error"
    assert classify_asr_error("hello", "जोजोलोपा", profile, "devanagari", "wrong_target_language")["error_type"] == "wrong_language_detection"
    assert classify_asr_error("घर", "थर", profile, "devanagari", "no_drift")["error_type"] == "lexical_substitution"


def test_data_quality_tiers():
    profile = load_language_profile("newari")

    assert assign_training_tier(0.9, 0.6, True, True, True, "base_language_drift", "word_boundary_error", profile)["training_tier"] == "gold"
    assert assign_training_tier(0.8, 0.9, True, False, True, "no_drift", None, profile)["training_tier"] == "silver"
    assert assign_training_tier(0.8, 0.4, False, False, True, "low_confidence", None, profile)["training_tier"] == "bronze"
    assert assign_training_tier(0.9, 0.9, True, True, False, "no_drift", None, profile)["training_eligible"] is False


@pytest.mark.asyncio
async def test_training_exporter_exports_only_gold_and_metadata(db_session, monkeypatch):
    from services import training_exporter

    export_root = Path(".test-exports") / str(uuid.uuid4())
    monkeypatch.setattr(training_exporter, "EXPORT_ROOT", export_root)
    teacher_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    gold_message_id = str(uuid.uuid4())
    rejected_message_id = str(uuid.uuid4())

    db_session.add(
        User(
            id=teacher_id,
            email="teacher@example.com",
            first_name="Teacher",
            primary_language="nepali",
        )
    )
    db_session.add(
        TeachingSession(
            id=session_id,
            teacher_id=teacher_id,
            country_code="NP",
            target_language="newari",
            base_asr_languages=["ne", "en"],
        )
    )
    db_session.add_all(
        [
            Message(
                id=gold_message_id,
                session_id=session_id,
                teacher_id=teacher_id,
                turn_index=0,
                role="teacher",
                text="जोजोलोपा",
                country_code="NP",
                target_language="newari",
                script="devanagari",
                raw_stt="जो जो लो पा",
                teacher_corrected_transcript="जोजोलोपा",
                normalized_transcript="जोजोलोपा",
                training_tier="gold",
                training_eligible=True,
                consent_training_use=True,
                audio_path="/audio/one.wav",
                audio_duration_ms=1000,
            ),
            Message(
                id=rejected_message_id,
                session_id=session_id,
                teacher_id=teacher_id,
                turn_index=1,
                role="teacher",
                text="bad",
                country_code="NP",
                target_language="newari",
                training_tier="rejected",
                training_eligible=False,
                consent_training_use=True,
            ),
        ]
    )
    await db_session.commit()

    result = await training_exporter.export_training_rows(
        db_session,
        country_code="NP",
        target_language="newari",
        tier="gold",
    )

    export_path = Path(result["export_path"])
    rows = [json.loads(line) for line in export_path.read_text(encoding="utf-8").splitlines()]
    assert result["sample_count"] == 1
    assert rows[0]["message_id"].replace("-", "") == gold_message_id.replace("-", "")
    assert rows[0]["training_tier"] == "gold"
    assert (export_path.parent / "metadata.jsonl").exists()
    shutil.rmtree(export_root.parent, ignore_errors=True)


def test_adapter_readiness_thresholds():
    base = {
        "country_code": "NP",
        "target_language": "newari",
        "silver_audio_hours": 0.0,
        "gold_utterance_count": 0,
        "unique_teacher_count": 1,
        "speaker_diversity_score": 0.1,
        "dialect_diversity_score": 0.1,
        "correction_rate": 0.1,
        "drift_rate": 0.2,
        "dominant_error_type": "word_boundary_error",
        "domain_coverage_score": 0.1,
    }

    assert compute_adapter_readiness(gold_audio_hours=4.9, **base)["readiness_level"] == "collect_only"
    assert compute_adapter_readiness(gold_audio_hours=5.0, **base)["readiness_level"] == "experimental_adapter_ready"
    assert compute_adapter_readiness(gold_audio_hours=50.0, **base)["readiness_level"] == "production_adapter_ready"
