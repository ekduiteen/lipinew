# Language-Adaptive ASR

LIPI is a multilingual speech-data platform where the user is the teacher and LIPI is the student. The ASR system is country-anchored: it starts from a country's reliable base language anchors, then adapts toward the teacher-selected target language through verified corrections.

## Architecture

```text
LIPI Core
  -> Country Profile
  -> Teacher Session Contract
  -> ASR Candidate Router
  -> Teacher Correction
  -> Error Intelligence
  -> Data Quality Gate
  -> Training Export
  -> Adapter Readiness
  -> Active Data Collection
```

For Nepal, the ASR anchor is always Nepali + English:

```json
{
  "country_code": "NP",
  "base_asr_languages": ["ne", "en"],
  "target_language": "newari",
  "bridge_language": "ne",
  "script": "devanagari",
  "dialect_label": "Patan Newar",
  "teaching_mode": "household_speech",
  "allow_code_switching": true,
  "consent_training_use": true
}
```

## Registries

Country profiles live in `backend/config/country_profiles.json`. Nepal is the first full profile; India, Japan, Indonesia, and the Philippines are placeholders for future expansion.

Language profiles live in `backend/config/language_profiles.json`. Language-specific behavior must come from profiles, not hardcoded Newari logic. Profiles define inheritance, scripts, bridge languages, adapter status, tokenizer type, normalization rules, error taxonomy, quality thresholds, and prompt notes.

## ASR Candidates

STT returns a selected transcript for backward compatibility and a full candidate list for storage:

```json
{
  "selected_transcript": "...",
  "selected_language": "ne",
  "detected_language": "ne",
  "target_language": "newari",
  "base_asr_languages": ["ne", "en"],
  "confidence": 0.62,
  "needs_teacher_confirmation": true,
  "asr_drift_type": "base_language_drift",
  "candidates": [
    {"candidate_type": "base_nepali", "language_code": "ne", "transcript": "..."},
    {"candidate_type": "base_english", "language_code": "en", "transcript": "..."},
    {"candidate_type": "whisper_auto", "language_code": "ne", "transcript": "..."}
  ]
}
```

All candidates are stored in `asr_candidates`. Whisper auto-detection is evidence only.

## Database Fields

`teaching_sessions` stores country, target language, bridge language, script, dialect label, teaching mode, consent, base ASR languages, and the full `session_language_contract`.

`messages` stores language metadata, selected/detected language, drift type, confidence, teacher verification, raw STT, base/English/target transcripts, normalized transcript, teacher correction, correction error type/family, and training tier.

New tables:
- `asr_candidates`
- `asr_error_events`
- `text_corpus_items`
- `training_exports`

## Correction And Tiering

Correction actions:
- Accept transcript: teacher verified, silver if high confidence and clean
- Edit transcript: teacher correction becomes gold if consent and quality gates pass
- Wrong language: creates `wrong_language_detection` error event
- Skip: not saved as verified training data

Training tiers:
- `gold`: teacher-corrected, verified, consented, clean
- `silver`: teacher-accepted, high confidence, clean, no major drift
- `bronze`: archive/review only
- `rejected`: no consent, unusable, unsafe, wrong language without correction, or very poor audio

## Training Export

CLI:

```bash
python scripts/export_training_data.py --country NP --language newari --tier gold
python scripts/export_training_data.py --country NP --all-languages --tier gold
```

ASR JSONL rows include message/audio IDs, country, target language, base ASR languages, script, dialect, raw STT, candidate transcripts, teacher correction, normalized transcript, tier, drift, error type, confidence, teacher ID, consent, and timestamp.

Future augmentation manifest:

```bash
python scripts/prepare_asr_augmentation_manifest.py --export-dir /data/exports/NP/newari --include-silver
```

Only gold and selected silver rows are eligible.

## Dashboard Metrics

`GET /api/dashboard/language-adaptive` returns:
- Language overview: clean hours, gold/silver/bronze/rejected counts
- ASR drift: drift rate by language and drift type
- Error intelligence: error frequency by language/script/severity
- Adapter readiness: readiness level, gold hours, unique teachers, dominant error
- Teacher contribution: corrections, accepted gold samples, dialect coverage
- Data quality: tier ratios, audio quality, STT confidence, correction rate

## Future Adapter Training

Adapter readiness levels:
- `collect_only`: under 5 gold hours
- `experimental_adapter_ready`: at least 5 gold hours
- `benchmark_ready`: at least 20 gold hours
- `production_adapter_ready`: at least 50 gold hours
- `dialect_adapter_ready`: at least 200 gold hours plus dialect diversity

Active prompt planning uses dominant error type and coverage gaps to ask teachers for the next useful data, such as word-boundary probes, nasalized pairs, clean target-language-only phrases, or code-switch annotation.
