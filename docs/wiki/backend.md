# Backend

## Role

`backend/` is the product core. It owns FastAPI routes, WebSocket conversation handling, auth, learning, moderation, analytics, persistence, and integrations to ML/LLM/storage.

## Important Entry Points

- `backend/main.py`: app setup, middleware, health, router registration, lifespan workers.
- `backend/config.py`: env-backed settings.
- `backend/db/connection.py`: async SQLAlchemy engine/session.
- `backend/dependencies/auth.py`: public user auth and WebSocket token handling.
- `backend/dependencies/admin_auth.py`: admin auth.
- `backend/routes/`: REST and WebSocket route layer.
- `backend/services/`: business logic and integration layer.
- `backend/models/`: ORM models.
- `backend/alembic/versions/`: migrations.
- `backend/tests/`: backend test suite.

## Routers

| Router | Prefix/surface | Responsibility |
|---|---|---|
| `auth.py` | `/auth/*` | Google/demo auth, refresh, WebSocket token |
| `teachers.py` | `/teachers/*` | onboarding, teacher stats, badges |
| `sessions.py` | `/api/sessions`, `/ws/session/*` | session creation, correction submission, live conversation |
| `leaderboard.py` | `/leaderboard` | ranking data |
| `dashboard.py` | `/dashboard/*` | public/system dashboard summaries |
| `phrases.py` | `/api/phrases/*` | phrase lab next/submit/skip/generate/review |
| `heritage.py` | `/heritage/*` | guided heritage capture |
| `admin_auth.py` | `/api/ctrl/auth/*` | control dashboard login |
| `admin_moderation.py` | `/api/ctrl/moderation/*` | review queue, labels, batch actions, gold records |
| `admin_export.py` | `/api/ctrl/datasets/*` | snapshot creation/download |
| `admin_system.py` | `/api/ctrl/system/*` | admin health, audit, metrics, keyterm seeds, intelligence overview |

## Service Groups

| Group | Services |
|---|---|
| Audio and speech | `stt.py`, `tts.py`, `audio_storage.py`, `audio_understanding.py`, `speaker_embeddings.py`, `speaker_clustering.py` |
| Conversation intelligence | `hearing.py`, `turn_interpreter.py`, `input_understanding.py`, `intent_classifier.py`, `entity_extractor.py`, `turn_intelligence.py` |
| Prompt/response | `prompt_builder.py`, `active_prompt_planner.py`, `behavior_policy.py`, `response_orchestrator.py`, `response_cleanup.py`, `post_generation_guard.py`, `personality.py`, `routing_hooks.py` |
| Memory/learning | `memory_service.py`, `topic_memory.py`, `learning.py`, `training_capture.py`, `message_store.py`, `correction_graph.py`, `teacher_modeling.py` |
| Curriculum and diversity | `curriculum.py`, `curriculum_seed.py`, `diversity.py`, `keyterm_service.py` |
| Language-adaptive ASR | `country_registry.py`, `language_registry.py`, `text_normalization.py`, `asr_drift.py`, `asr_error_classifier.py`, `data_quality.py`, `adapter_readiness.py`, `training_exporter.py` |
| Gamification | `points.py`, `badges.py` |
| Admin/control | `admin_auth.py`, `admin_moderation.py`, `admin_export.py` |
| Model calls | `llm.py` |
| Phrase/heritage | `phrase_pipeline.py`, `phrase_generator.py`, `heritage_prompt.py` |

## Backend Rules

- Use Valkey, not Redis imports.
- Points transactions are immutable; summaries are derived.
- Use async SQLAlchemy sessions and `httpx`, not sync request code in runtime paths.
- Dynamic prompts are assembled from teacher/session/memory/policy context.
- Corrections and approved rules carry highest learning weight.
- Low-confidence or single-teacher extractions should move toward review, not blind learning.
- Admin actions must stay audited through admin models/services.

## Background Work

`backend/main.py` starts:

- point-summary rebuild loop every 5 minutes
- learning worker from `services.learning`
- phrase auto-generation worker from `services.phrase_generator`

These depend on shared HTTP client, DB sessions, and Valkey queue keys from settings.

