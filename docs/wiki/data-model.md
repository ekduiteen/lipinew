# Data Model

## Source Of Truth

Use [DATABASE_SCHEMA.md](../../DATABASE_SCHEMA.md) for detailed table fields and migration history. This page maps ownership and relationships.

## Model Groups

| Group | Models/files | Purpose |
|---|---|---|
| Identity/session | `User`, `TeachingSession` | teacher profile and live session state |
| Message storage | `Message` | raw and derived per-turn data |
| Intelligence | `CorrectionEvent`, `TeacherSignal`, `SessionMemorySnapshot`, `UsageRule`, `MessageAnalysis`, `MessageEntity` | learning and turn-understanding state |
| Curriculum | `UserCurriculumProfile`, `UserTopicCoverage`, `GlobalLanguageCoverage`, `CurriculumPromptEvent` | coverage and prompt planning |
| Vocabulary | `VocabularyEntry`, `VocabularyTeacher` | extracted or approved vocabulary knowledge |
| Gamification | `PointsTransaction`, `TeacherPointsSummary`, `Badge`, `TeacherBadge` | points, streaks, badges |
| Phrase Lab | `Phrase`, `PhraseSubmission`, related phrase models | structured phrase recording data |
| Heritage | `HeritageSession` | guided heritage/dialect capture |
| ASR/training | `ASRCandidate`, `ASRErrorEvent`, `TextCorpusItem`, `TrainingExport` | language-adaptive ASR and export prep |
| Review/gold | `ReviewQueueItem`, `GoldRecord`, `DatasetSnapshot` | moderation and curated data |
| Admin | `AdminAccount`, `AdminAuditLog` | control dashboard security/audit |

## Persistence Rules

- `messages` keeps raw transcript plus derived quality/intelligence fields.
- `message_analysis` and `message_entities` normalize intent/entity extraction.
- `correction_events` and `usage_rules` are high-value learning sources.
- `review_queue_items` are the buffer between uncertain extraction and trusted knowledge.
- `dataset_gold_records` are curated, moderated output.
- `dataset_snapshots` represent export artifacts, not live state.
- `points_transactions` are append-only; summaries are rebuilt.

## Migrations

Alembic lives under `backend/alembic/`.

Current migration themes include:

- initial schema
- phrase lab and review queue
- heritage sessions
- curriculum/diversity
- vocabulary reliability
- intelligence layer core
- admin queue claims/metrics
- training data capture
- turn intelligence
- language-adaptive ASR

## Storage Outside Postgres

MinIO stores large blobs and archives:

- raw user audio
- generated TTS output
- export archives

Valkey stores ephemeral state:

- learning queues
- cached session message history
- cached profile/tone state
- processing/dead-letter queue metadata

