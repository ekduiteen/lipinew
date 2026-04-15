# LIPI Database Schema

This is the **current practical schema reference** for the live LIPI backend.

The source of truth is:
- ORM models in `backend/models/`
- Alembic migrations in `backend/alembic/versions/`
- `init-db.sql` for first-run bootstrap

## Core Product Tables

### `users`
Teacher identity, onboarding profile, consent, trust signals.

Important fields:
- `primary_language`
- `other_languages`
- `hometown`
- `credibility_score`
- consent flags

### `teaching_sessions`
Per-session metadata.

Important fields:
- `teacher_id`
- `register_used`
- `started_at`, `ended_at`

### `messages`
Permanent per-turn log for both teacher and LIPI.

Important fields:
- `session_id`
- `teacher_id`
- `turn_index`
- `role`
- `text`
- `detected_language`
- `audio_path`
- `audio_duration_ms`
- `stt_confidence`
- `llm_model`
- `llm_latency_ms`

Training-data capture fields:
- `raw_signals_json`
- `derived_signals_json`
- `high_value_signals_json`
- `style_signals_json`
- `prosody_signals_json`
- `nuance_signals_json`

These fields are how each teacher turn now stores:
1. raw data
2. derived language/style/dialect signals
3. high-value learning signals

## Intelligence Layer Tables

### `user_curriculum_profiles`
Per-user curriculum / lane / register state.

### `user_topic_coverage`
Per-user topic history and confidence.

### `global_language_coverage`
Global topic/register/language coverage scoring.

### `curriculum_prompt_events`
What LIPI asked, why it asked it, and whether the teacher answered/corrected it.

### `correction_events`
The correction graph.

Tracks:
- wrong claim
- corrected claim
- wrong message
- correction message
- topic
- confidence before / after

### `session_memory_snapshots`
Durable structured memory snapshots.

Tracks:
- active language
- active topic
- recent taught words
- recent corrections
- unresolved misunderstandings
- next follow-up goal
- `style_memory_json`

### `teacher_credibility_events`
Audit trail of teacher credibility changes over time.

### `teacher_signals`
Per-turn structured teacher-signal trail.

Used for:
- language mix tracking
- dialect tendency tracking
- register tendency tracking
- tone / speech rate / prosody observations

Important fields:
- `signal_type`
- `signal_key`
- `signal_value_json`
- `confidence`
- `source`

### `knowledge_confidence_history`
How confidence in learned knowledge changes over time.

### `usage_rules`
Extracted usage/correction notes that can become future product knowledge.

## Gamification Tables

### `points_transactions`
Immutable points log.

### `teacher_points_summary`
Cached aggregate points/streak summary.

### `badges`
Badge definitions.

### `teacher_badges`
Earned badges per teacher.

### `leaderboard_snapshots`
Periodic leaderboard state.

## Learning Tables

### `vocabulary_entries`
Words LIPI has learned.

### `vocabulary_teachers`
Which teachers contributed to each word.

## Audio / Dialect Tables

### `speaker_embeddings`
Async speaker/acoustic signature store for dialect clustering and future speaker similarity work.

Current status:
- table exists
- async extraction pipeline is implemented
- backend learning worker fetches teacher audio from MinIO and writes `vector(512)` rows
- current embedding source is `acoustic_signature_v1`, a lightweight deterministic 512-d acoustic signature
- lightweight incremental cluster assignment is live via `dialect_cluster_id`
- intended next phase is stronger clustering analysis and later dialect-aware routing

## Migrations

Recent important migrations:
- `91ba4c4fe766_initial_schema.py`
- `d3f4c6b8a921_curriculum_and_diversity_engine.py`
- `e4b7f9a21c10_intelligence_layer_core.py`
- `f1c2d8b44a11_training_data_capture_signals.py`

## Practical Rule

If you add or change schema:
1. update ORM models
2. add Alembic migration
3. update this file
4. update `DEV_ONBOARDING.md` if the turn flow or service graph changes
