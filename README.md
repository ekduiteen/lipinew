# LIPI

LIPI is a **community-powered language data collection platform disguised as a conversation**.

LIPI is the student. Users are the teachers.

Every turn has to do two jobs:
- feel good enough that the teacher wants to come back
- produce language data that is actually worth keeping

## Current Product State

The app is working end-to-end:
- auth
- onboarding
- live Teach screen
- phrase lab capture flow
- WebSocket conversation loop
- STT / LLM / TTS integration
- points / badges / leaderboard
- durable learning queue
- dashboard visibility
- multi-engine backend intelligence layer
- Native Android App Wrapper (Capacitor)

The main problems are no longer infrastructure problems. They are product-quality problems:
- STT quality, especially for Newari and mixed turns
- response feel still too rigid or over-confirming
- voice quality and language-specific TTS delivery
- data cleanliness for future fine-tuning

## Live Stack

### Local
- frontend on `http://127.0.0.1:3000`
- backend on `http://127.0.0.1:8000`
- postgres / valkey / minio in Docker

### Remote
- one NVIDIA L40S
- backend-expected model endpoint currently on `127.0.0.1:8210`
- Docker `backend`, `ml`, `postgres`, `valkey`, `minio`

### Core runtime
- **LLM**: Gemma 4 via an OpenAI-compatible shim
- **STT**: faster-whisper large-v3
- **TTS**: Piper

Current voice direction:
- keep Nepali voice as `ne_NP-google-medium`
- route English through a separate English Piper voice
- do not go back to OmniVoice on the live path

Current ops note as of 2026-04-20:
- local and remote services are running
- remote backend and ML are healthy
- remote backend is configured for `:8210`
- local hybrid dev keeps `:8100` only as a local tunnel convenience port mapped to remote `:8210`
- local and remote DBs are reconciled to Alembic head `f2a3b4c5d6e7`

## Intelligence Layer

LIPI now runs as a backend intelligence system, not just a prompt.

Main engines:
- Hearing Engine
- Turn Interpreter
- Input Understanding Layer
- Audio Understanding Sidecar
- Teacher Modeling Layer
- Structured Session Memory
- Correction Graph
- Behavior Policy Engine
- Personality Engine
- Curriculum Engine
- Diversity Engine
- Learning Engine
- Post-Generation Guard
- Training Data Capture System
- Phrase Lab Pipeline
- Heritage Prompt Generator

Key files:
- [backend/routes/sessions.py](backend/routes/sessions.py)
- [backend/services/hearing.py](backend/services/hearing.py)
- [backend/services/turn_interpreter.py](backend/services/turn_interpreter.py)
- [backend/services/input_understanding.py](backend/services/input_understanding.py)
- [backend/services/teacher_modeling.py](backend/services/teacher_modeling.py)
- [backend/services/memory_service.py](backend/services/memory_service.py)
- [backend/services/correction_graph.py](backend/services/correction_graph.py)
- [backend/services/behavior_policy.py](backend/services/behavior_policy.py)
- [backend/services/response_orchestrator.py](backend/services/response_orchestrator.py)
- [backend/services/personality.py](backend/services/personality.py)
- [backend/services/curriculum.py](backend/services/curriculum.py)
- [backend/services/diversity.py](backend/services/diversity.py)
- [backend/services/response_cleanup.py](backend/services/response_cleanup.py)
- [backend/services/post_generation_guard.py](backend/services/post_generation_guard.py)
- [backend/services/admin_moderation.py](backend/services/admin_moderation.py)
- [backend/services/admin_export.py](backend/services/admin_export.py)
- [backend/services/audio_storage.py](backend/services/audio_storage.py)
- [backend/services/learning.py](backend/services/learning.py)
- [backend/services/heritage_prompt.py](backend/services/heritage_prompt.py)
- [backend/services/phrase_pipeline.py](backend/services/phrase_pipeline.py)

Every teacher turn now produces structured capture layers:
- raw data (Messages)
- derived signals (TeacherSignals)
- high-value learning signals (CorrectionEvents)
- **verified ground-truth (GoldRecords)** via the Control Dashboard

LIPI now has four collection modes:
- `Teach`: open-ended student/teacher conversation (original)
- `Heritage`: structured dialect/register capture via guided prompts (Guided)
- `Phrase Lab`: structured phrase and variation capture for cleaner supervised data (Guided)
- **`Gold Curation`**: expert-human moderation and labeling in the Enterprise Dashboard.

## Control Stack

The platform now includes a standalone administrative and analyst environment:
- **frontend-control** on `http://127.0.0.1:3001` (Enterprise Dashboard)
- **Admin Security**: Isolated `AdminAccount` and `AdminAuditLog` system.
- **Moderation**: claim-safe review queue with filtering, batch actions, and prefetched claimed buffers.
- **Deep Analytics**: DB-derived moderation and throughput metrics.
- **Factory**: versioned dataset snapshot logic with authenticated MinIO-backed download flow.

The newest learning direction is also more conservative:
- correction-derived rules are moving toward a review queue instead of being blindly trusted
- audio-understanding sidecar signals are optional enrichment, not a hard dependency for the live path

## Turn Intelligence State

As of 2026-04-18, intent recognition, entity extraction, and keyterm boosting are first-class parts of the product.

What is now live:
- per-turn intent recognition with confidence and secondary labels
- structured entity extraction for vocabulary, phrases, register terms, language names, corrected terms, glosses, and examples
- session-aware keyterm preparation from memory, teacher history, admin seeds, and uncertain terms
- cautious transcript repair for low-confidence critical words
- normalized persistence in `message_analysis` and `message_entities`
- dashboard and control visibility for intent distribution, entity counts, keyterm hit quality, and low-signal rate

This preserves the product philosophy:
- LIPI remains the student
- the user remains the teacher
- low-signal turns do not get treated as strong learning
- corrections still carry the highest learning weight

## Verified Activation State

As of 2026-04-18, the highest-value dormant intelligence paths are now active and re-verified:
- approved corrections update persistent knowledge state
- approved corrections produce approved `UsageRule` rows that are reloaded into future sessions
- cross-session memory is loaded from durable `session_memory_snapshots` at session start
- approved prior teachings are injected into per-turn prompt guidance
- low-trust vocabulary extractions are rejected from direct learning and queued for review
- single-teacher vocabulary confidence is capped until stronger validation arrives

Verification outcome:
- activation-focused backend tests: passing
- targeted runtime probes: passing for approval flow, memory load, prompt injection, extraction validation, and confidence cap
- one unrelated legacy test still fails in `backend/tests/test_intelligence_layer.py` on `secondary_languages` expectations

Important implementation note:
- app frontend server routes no longer assume `localhost` or `backend:8000`
- control frontend no longer hardcodes `localhost`, but it now requires `BACKEND_URL` or `NEXT_PUBLIC_API_URL`
- set backend URL env vars explicitly for both Next.js apps
- local backend dev now relies on `docker-compose.dev.yml` overrides that mount `.env` and exclude transient pytest temp directories from Uvicorn reload watching
- remote backend deploys should sync committed source to `/data/lipi` and rebuild, not assume the remote host is a clean git checkout

## Development And Deploy Discipline

The stable loop is now:
- develop locally with local backend on `:8000`
- tunnel only remote ML/model services when needed
- commit backend changes before remote deploy
- sync committed source to remote `/data/lipi`
- rebuild remote backend image
- verify remote backend `/health`, remote ML `/health`, and remote `:8210/v1/models`

The main ops failure on 2026-04-20 was not product logic. It was source drift plus a stale remote compose `DATABASE_URL` pointing at an old container IP. The backend must use localhost-published services on the remote host.

## Admin / Data Operations State

As of 2026-04-18, the control system is no longer just a moderation panel.

Operational capabilities now live in code:
- queue claiming with expiry and auto-release
- filtered moderation queue by review type, language, confidence, source, and age
- atomic batch approve / reject / release actions
- real moderation metrics via `/api/ctrl/system/metrics/real`
- audited dataset snapshot creation with filters for language, dialect, date range, and confidence threshold
- authenticated artifact download via `/api/ctrl/datasets/download/{snapshot_id}` and the control frontend proxy
- moderation UI now surfaces review type, source, confidence, teacher credibility, and supporting-teacher signal
- gold browser now shows provenance and confidence history

Current control-system verification:
- backend admin-control tests passing
- `frontend-control` production build passing
- moderation path safe for multiple reviewers at the claim/action layer

## Canonical Docs

This repo used to have many overlapping setup/status/handover files. The canonical set is now:

- [CLAUDE.md](CLAUDE.md)
  Product and engineering source of truth.
- [LIPI_PHILOSOPHY.md](LIPI_PHILOSOPHY.md)
  Why LIPI exists and how the student-teacher dynamic should feel.
- [DEV_ONBOARDING.md](DEV_ONBOARDING.md)
  Architecture, services, runtime layout, turn flow, and developer workflow.
- [OPERATIONS.md](OPERATIONS.md)
  Actual deployment, restart, health-check, and remote-server operations guide.
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
  Schema reference.
- [PHASE_ROADMAP.md](PHASE_ROADMAP.md)
  Product build order and upcoming work.
- [HANDOVER_TO_CODEX.md](HANDOVER_TO_CODEX.md)
  Short current-state handover for the next engineer.
- [SYSTEM_STATUS_REPORT.md](SYSTEM_STATUS_REPORT.md)
  Comprehensive health check and deployment status (updated regularly).

If you add a new service, architecture change, deployment pattern, or workflow, update one of the docs above instead of creating a new summary file.

## Honest Status

The backend intelligence is much stronger than it was a few weeks ago. The remaining gaps are mostly:
- speech quality
- STT reliability
- delivery tone
- multilingual data quality

The right mindset for the next phase is:

**make LIPI feel like a believable multilingual student whose conversations are worth collecting.**
