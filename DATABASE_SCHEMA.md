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

### `message_analysis`
Normalized per-message turn intelligence.

Tracks:
- `intent_label`
- `intent_confidence`
- `secondary_intents_json`
- `primary_language`
- `secondary_language`
- `code_switch_json`
- `quality_json`
- `keyterms_json`
- `transcript_original`
- `transcript_final`
- `transcript_repair_metadata`

Current use:
- written for teacher turns in the teach loop and refreshed by the async learning worker
- read by dashboard analytics and admin intelligence overview

### `message_entities`
Structured entities extracted from a teacher turn.

Tracks:
- raw `text`
- `normalized_text`
- `entity_type`
- `language`
- `confidence`
- `source_start` / `source_end`
- `attributes_json`

Current use:
- powers vocabulary persistence, gloss capture, register tracking, correction targets, and dashboard entity analytics

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

### `admin_keyterm_seeds`
Admin-curated keyterm seed lists for STT prompting, transcript repair, and extraction boosting.

Tracks:
- `language_key`
- `term`
- `normalized_term`
- `entity_type`
- `weight`
- `is_active`
- optional metadata JSON

Current use:
- merged into per-turn keyterm candidates before STT
- exposed in admin system endpoints for visibility and curation

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

## Phrase Lab Tables

### `phrases`
Structured prompt library for phrase capture.

### `phrase_generation_batches`
Batch provenance for generated phrase sets.

### `phrase_submission_groups`
Tracks the lifecycle of one phrase prompt across primary + variation capture.

### `phrase_submissions`
Stores structured phrase-lab recordings plus derived language, dialect, prosody, and quality signals.

### `phrase_skip_events`
Tracks skipped prompts so selection can avoid repetition.

### `phrase_reconfirmation_queue`
Schedules phrases that should be re-asked after uncertain or low-confidence capture.

### `phrase_metrics`
Aggregate coverage and quality counters for phrase prompts.

## Heritage Tables

### `heritage_sessions`
Isolates long-form cultural/language storytelling and explanation from standard daily conversational learning.

- **Purpose**: Stores the chosen contribution mode (e.g. Story, Word Explanation) and the resulting LLM prompt.
- **Why**: Protects `teaching_sessions` performance metrics from being artificially skewed by long heritage answers.
- **Includes**: Primary recording paths and follow-up paths.

## Review / Approval Tables

### `review_queue_items`
Human-in-the-loop review queue for extracted correction claims and future rule approval.

Current use:
- correction-derived rules can be staged for approval instead of being blindly trusted
- low-trust extraction candidates are also staged here with `model_source = learning_validation_guard`

## Admin Control Tables

### `admin_accounts`
Isolated administrative accounts for LIPI staff. Not part of the teacher user base.

### `admin_audit_logs`
Detailed audit trail for every administrative action (labeling, exporting, banning).

## Dataset Curation (The Gold Layer)

### `dataset_gold_records`
The foundational training repository. Contains human-verified transcripts, dialect labels, and quality scores snapshotted from the conversational history.

### `dataset_snapshots`
Versioned "releases" of training data (e.g., `v1.2-stt-ktm`) with download links to MinIO artifacts.

## Migrations

Recent important migrations (in order):
- `91ba4c4fe766_initial_schema.py` — Core tables (users, sessions, messages)
- `d3f4c6b8a921_curriculum_and_diversity_engine.py` — Curriculum state and coverage
- `e4b7f9a21c10_intelligence_layer_core.py` — Correction events, session memory, teacher signals
- `f1c2d8b44a11_training_data_capture_signals.py` — Training data envelopes (raw/derived/high-value)
- `a7c6e1d9f210_phrase_lab_and_review_queue.py` — Phrase Lab tables + review queue (NEW)
- `b8d7e4c3f920_heritage_sessions.py` — Heritage mode tables (NEW)
- `c9d8e7f6a5b4_admin_and_gold_layer.py` — Admin auth, Gold records, and Audit logs (NEW)
- `d1e2f3a4b5c6_vocabulary_reliability.py` — vocabulary reliability controls + approval index
- `e6f7a8b9c0d1_admin_queue_claims_and_metrics.py` — queue claims, moderation indexes, real control metrics support
- `f2a3b4c5d6e7_turn_intelligence_layer.py` — message analysis, message entities, admin keyterm seeds, seed bootstrap

## Turn Intelligence Storage Rules

The production path for teacher-turn analysis is now:
1. `messages` stores the canonical transcript and capture envelopes
2. `message_analysis` stores intent, keyterms, code-switch, repair metadata, and learning usability
3. `message_entities` stores extracted typed entities
4. `knowledge_confidence_history` records persistence-confidence changes caused by corrected or learned knowledge

This separation is intentional:
- `messages` remains the immutable conversation log
- `message_analysis` is the normalized analytical view
- `message_entities` keeps entity analytics queryable without unpacking JSON

## Practical Rule

If you add or change schema:
1. update ORM models
2. add Alembic migration
3. update this file
4. update `DEV_ONBOARDING.md` if the turn flow or service graph changes
