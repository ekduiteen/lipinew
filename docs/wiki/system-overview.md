# System Overview

## Product Shape

LIPI is built around one product rule: LIPI is the student, the user is the teacher. The product collects high-value language data through teaching behaviors instead of generic labeling tasks.

Core collection modes:

- Teach: open-ended live conversation over WebSocket.
- Heritage: guided cultural, dialect, and register capture.
- Phrase Lab: structured phrase and variation audio capture.
- Gold Curation: internal expert moderation and dataset labeling.

## Main Applications

| Area | Directory | Audience | Responsibility |
|---|---|---|---|
| Public app | `frontend/` | Teachers/contributors | Auth, onboarding, Teach, Heritage, Phrase Lab, ranks, settings |
| API/backend | `backend/` | All apps/services | Auth, sessions, learning, intelligence, DB, admin APIs, exports |
| Control dashboard | `frontend-control/` | Internal staff | Moderation, analytics, health, audit, gold records, exports |
| ML service | `ml/` | Backend | STT, TTS, speaker embedding |
| Infrastructure | root compose/Caddy/monitoring | DevOps | Postgres, Valkey, MinIO, Prometheus, Grafana, proxy |

## Runtime Dependencies

- Postgres 16 + pgvector image: durable state.
- Valkey 8: cache, queues, session message history, learning worker queue.
- MinIO: audio, TTS artifacts, dataset archives.
- vLLM/OpenAI-compatible LLM endpoint: conversational generation.
- ML FastAPI service: faster-whisper STT, Piper/Coqui TTS, speaker embeddings.
- Docker Compose: local and remote orchestration.

## Core Outcomes

Every useful turn can produce several layers:

- raw message and audio metadata
- STT candidate/quality metadata
- intent and entity analysis
- correction events and usage rules
- teacher credibility signals
- curriculum/topic coverage
- review queue items
- gold records after moderation
- exportable training snapshots

## Where To Change Things

| Need | Start here |
|---|---|
| Conversation behavior | `backend/routes/sessions.py`, `backend/services/behavior_policy.py`, `backend/services/response_orchestrator.py`, `backend/services/prompt_builder.py` |
| STT quality | `backend/services/stt.py`, `ml/stt.py`, language/country profiles |
| TTS voice routing | `backend/services/tts.py`, `ml/tts.py`, `ml/tts_provider.py` |
| Learning from turns | `backend/services/learning.py`, `backend/services/training_capture.py`, `backend/services/message_store.py` |
| Moderation queue | `backend/routes/admin_moderation.py`, `backend/services/admin_moderation.py`, `frontend-control/src/app/(dashboard)/moderation/page.tsx` |
| Public UI | `frontend/app/(tabs)/`, `frontend/components/` |
| Admin UI | `frontend-control/src/app/(dashboard)/`, `frontend-control/src/components/` |
| Dataset export | `backend/routes/admin_export.py`, `backend/services/admin_export.py`, `backend/services/training_exporter.py` |

