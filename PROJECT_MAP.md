# LIPI Project Map

This document maps the current `lipiplan` repository as a code-and-operations reference. It reflects the codebase structure present in the workspace, including the production product (`frontend` + `backend` + `ml`), the enterprise moderation stack (`frontend-control`), supporting infrastructure, monitoring, scripts, and the large documentation surface.

---

## 1) Project Overview

### What LIPI is

LIPI is a multilingual language-data collection platform presented as a conversational student. The product framing is consistent across the repo: **LIPI is the student, the user is the teacher**. Instead of asking users to “label data,” the system turns teaching, correction, storytelling, phrase capture, and dialect variation into an interactive app experience.

### Core purpose

The repo is building two things at once:

1. a user-facing teaching product that feels believable and engaging enough for repeated use
2. a structured data engine that turns those conversations into usable speech, text, correction, vocabulary, and gold-labeled training data

The backend and docs repeatedly emphasize that each teacher turn should both:

- feel natural enough to keep the teacher engaged
- produce learning signals worth retaining for future model improvement

### Main target users

- **Primary teachers/contributors**: users speaking Nepali and related regional languages/dialects who teach LIPI through conversation
- **Heritage/dialect contributors**: users contributing targeted cultural, regional, and register-specific speech/text
- **Phrase Lab contributors**: users providing structured phrase/variation recordings for cleaner supervised datasets
- **Internal moderators/analysts/admins**: staff using `frontend-control` to review learning signals, approve/reject items, curate gold records, inspect metrics, and export dataset snapshots

### Product modes present in code

- **Teach**: live WebSocket conversation loop between teacher and LIPI
- **Heritage**: structured prompt flow for dialect/register/culture capture
- **Phrase Lab**: guided phrase recording and variation collection
- **Gold curation / moderation**: admin workflow to review queue items and create gold-standard records

### Current product state implied by the repo

The codebase is past the “can it run?” phase and into a quality-improvement phase. The system already includes:

- auth and onboarding
- session creation and live WS conversation
- STT / LLM / TTS integrations
- points, badges, leaderboard
- persistent learning and review queues
- phrase lab and heritage modules
- admin moderation/export system
- native Android wrapper via Capacitor
- monitoring and deploy scripts

The major remaining concerns are product quality: STT accuracy, response naturalness, voice delivery, and data cleanliness.

---

## 2) Tech Stack

### Languages

- **Python**: backend and ML services
- **TypeScript**: both Next.js frontends
- **JavaScript**: config/test/support files in frontend apps
- **SQL**: `init-db.sql`, PostgreSQL schema initialization
- **Bash/Shell**: deployment, setup, health-check scripts
- **CSS / CSS Modules / Tailwind CSS 4**: frontend styling
- **Docker Compose YAML**: environment orchestration
- **Caddyfile syntax**: reverse proxy configuration

### Backend stack

- **FastAPI** for REST + WebSocket APIs
- **Pydantic v2 / pydantic-settings** for validation and environment config
- **SQLAlchemy asyncio** for ORM/data access
- **Alembic** for schema migrations
- **asyncpg** for PostgreSQL connectivity
- **pgvector** image usage at infra level
- **Valkey** client for cache/queue/session state
- **MinIO** client for S3-compatible object storage
- **httpx** for service-to-service and model API calls
- **python-jose**, **Authlib**, **passlib/bcrypt** for auth/JWT/password handling
- **slowapi** for rate limiting
- **websockets** support
- **pytest / pytest-asyncio / aiosqlite** for tests

### Frontend stack (`frontend`)

- **Next.js 14.2.15**
- **React 18.3.1**
- **TypeScript 5**
- **next-pwa** for PWA/service worker support
- **Capacitor 8** for Android wrapper
- **Jest + Testing Library** for unit/component tests
- CSS Modules + global CSS, custom design primitives

### Control frontend stack (`frontend-control`)

- **Next.js 16.2.4**
- **React 19.2.4**
- **TypeScript 5**
- **Axios**
- **cookie-cutter**
- **lucide-react**
- **recharts**
- **wavesurfer.js**
- **Tailwind CSS 4**
- **clsx + tailwind-merge**

### ML stack

- **FastAPI** microservice
- **faster-whisper** for STT
- **Torch / torchaudio**
- **Piper TTS**
- **Coqui XTTSv2**
- **soundfile / scipy / numpy**
- custom speaker embedding service

### Data / infrastructure

- **PostgreSQL 16**
- **pgvector image**
- **Valkey 8**
- **MinIO**
- **Docker / Docker Compose**
- **Caddy** reverse proxy
- **Prometheus**
- **Grafana**
- **NVIDIA CUDA runtime / GPU containers**
- **vLLM OpenAI-compatible server**

### Operational / delivery tools

- **Makefile**
- shell deployment/bootstrap/health scripts
- `.env` / `.env.example`
- Docker healthchecks and Compose profiles

---

## 3) Architecture

### High-level components

- `frontend/`: public teacher-facing application
- `backend/`: FastAPI API, WebSocket conversation engine, persistence, learning logic, admin endpoints
- `frontend-control/`: internal admin/moderation/analytics/export dashboard
- `ml/`: dedicated STT/TTS/speaker-embedding service
- `monitoring/`: Prometheus scrape config
- `scripts/`: deployment/server bootstrap/health tooling
- root Docker/Caddy/env files: environment orchestration and reverse proxying

### How the major parts relate

- The **public frontend** handles auth flow, onboarding, teacher dashboards, phrase lab, heritage capture, and live conversation UI.
- The **backend** owns auth, sessions, learning logic, routes, DB access, durable memory, moderation queue generation, export logic, and admin APIs.
- The **ML service** performs speech-to-text, text-to-speech, and speaker embedding extraction.
- The **LLM layer** is externalized behind an OpenAI-compatible endpoint (`vLLM_URL` or remote Gemma/Qwen host depending deployment mode/docs).
- The **control frontend** talks to the backend’s `/api/ctrl/*` endpoints for moderation, system metrics, snapshot exports, and gold data browsing.
- **Postgres** stores all durable product, learning, moderation, and analytics state.
- **Valkey** stores caches, queues, session context, and other fast-access state.
- **MinIO** stores raw audio, TTS output, and dataset export archives.
- **Prometheus/Grafana** can scrape service metrics when monitoring profile is enabled.

### Text-based data flow diagram

```text
Teacher
  |
  v
frontend (Next.js public app)
  |-- REST -> backend /api/*
  |-- WS   -> backend /ws/session/{session_id}
  |
  v
backend (FastAPI)
  |-- auth/session/profile/leaderboard/dashboard routes
  |-- conversation orchestration
  |-- phrase lab + heritage flows
  |-- moderation/export/admin APIs
  |
  |-- reads/writes -> PostgreSQL
  |-- caches/queues -> Valkey
  |-- stores/fetches audio + archives -> MinIO
  |-- calls -> ML service (/stt, /tts, /speaker-embed)
  |-- calls -> LLM endpoint (vLLM/OpenAI-compatible server)
  |
  v
Derived outputs
  |- messages
  |- turn intelligence
  |- correction events
  |- vocabulary / usage rules
  |- review queue items
  |- gold records / dataset snapshots

Internal staff
  |
  v
frontend-control (Next.js admin app)
  |
  v
backend /api/ctrl/*
  |
  +-> moderation queue
  +-> gold curation
  +-> analytics / system health
  +-> dataset snapshot export/download
```

### Runtime architecture notes

- `frontend` and `frontend-control` are separate applications with different dependency stacks and different audiences.
- `backend/main.py` starts background loops for point-summary rebuild, learning worker processing, and automatic phrase generation.
- The conversation path is WebSocket-driven and enriches turns with multiple services: hearing, interpretation, input understanding, teacher modeling, memory, behavior policy, response orchestration, cleanup, TTS, training capture, and turn intelligence persistence.
- Admin moderation and export are not bolt-ons; they are integrated with first-class models (`ReviewQueueItem`, `GoldRecord`, `DatasetSnapshot`, admin auth/audit tables).

---

## 4) Backend Deep Dive

The backend is a FastAPI application with async SQLAlchemy, Alembic migrations, REST + WebSocket endpoints, and a service-oriented internal structure.

### Top-level backend files

- `backend/main.py`: FastAPI entrypoint, CORS, rate limiting, upload-size middleware, health endpoint, startup/shutdown lifecycle, background workers, route registration
- `backend/config.py`: environment-driven settings model
- `backend/cache.py`: Valkey client setup
- `backend/jwt_utils.py`: JWT encode/decode helpers for user/admin tokens
- `backend/rate_limit.py`: slowapi limiter configuration
- `backend/alembic.ini`: Alembic config
- `backend/requirements.txt`: backend dependencies
- `backend/pytest.ini`: pytest config
- `backend/Dockerfile`: backend container image

### `backend/db/`

- `db/connection.py`: async engine/session factory and `get_db` dependency
- `db/init_db.py`: one-shot `Base.metadata.create_all()` initializer
- `db/__init__.py`: package marker

### `backend/dependencies/`

- `dependencies/auth.py`: user auth dependencies for REST and WebSocket, including flexible token resolution
- `dependencies/admin_auth.py`: admin bearer auth, admin lookup, and super-admin guard
- `dependencies/__init__.py`: package marker

### `backend/models/`

#### Core product models

- `models/user.py`: teacher identity, profile, language/background fields, trust/admin flags, consents
- `models/session.py`: `TeachingSession` lifecycle and aggregate counters
- `models/message.py`: per-turn message storage with raw/derived/high-value/style/prosody/nuance signal JSON fields
- `models/points.py`: points ledger and summary cache
- `models/badge.py`: badge definitions and teacher-earned badges

#### Intelligence / learning models

- `models/intelligence.py`: correction events, teacher signals, credibility history, memory snapshots, usage rules, message analysis/entities, admin seeds, review queue, vocabulary tables
- `models/curriculum.py`: user curriculum profile, topic coverage, global coverage, curriculum prompt events

#### Guided collection / curation models

- `models/phrases.py`: phrase generation, phrase catalog, submission groups/submissions, reconfirmation, skip events, phrase metrics
- `models/heritage.py`: heritage sessions and follow-up capture
- `models/dataset_gold.py`: gold-standard curated records and dataset snapshots
- `models/admin_control.py`: isolated admin accounts and audit logs

#### Base/init

- `models/base.py`: declarative base
- `models/__init__.py`: aggregate imports/export surface

### `backend/routes/`

- `routes/auth.py`: teacher auth/demo/google/token-related endpoints
- `routes/sessions.py`: session creation and core conversation WebSocket endpoint
- `routes/leaderboard.py`: leaderboard APIs
- `routes/teachers.py`: onboarding, teacher stats, teacher badges
- `routes/dashboard.py`: public/system dashboard overview endpoints
- `routes/phrases.py`: phrase lab APIs
- `routes/heritage.py`: heritage contribution APIs
- `routes/admin_auth.py`: admin login
- `routes/admin_moderation.py`: moderation queue, claim/release, label/reject, batch actions
- `routes/admin_export.py`: snapshot listing/creation/download
- `routes/admin_system.py`: admin metrics, seeds, health/ops endpoints
- `routes/__init__.py`: package marker

### `backend/services/` one-line descriptions

- `admin_auth.py`: authenticates internal admin accounts using stored password hashes
- `admin_export.py`: builds filtered gold-record snapshots, packages artifacts, and streams downloads from MinIO
- `admin_moderation.py`: implements queue claiming, filtering, approval/rejection, release, and gold-promotion workflows
- `audio_storage.py`: stores/fetches teacher and phrase audio in MinIO and checks bucket health
- `audio_understanding.py`: optional sidecar extraction of acoustic/dialect/tone signals with safe fallback behavior
- `badges.py`: checks summary thresholds and awards badges idempotently
- `behavior_policy.py`: turns teacher/memory understanding into concrete response-behavior rules
- `correction_graph.py`: persists approved corrections and usage rules and reloads them into later sessions
- `curriculum.py`: deterministic per-user curriculum and topic/question selection logic
- `curriculum_seed.py`: seeds taxonomy/coverage baseline data for curriculum systems
- `diversity.py`: tracks global coverage and diversity scoring across topics/registers/languages
- `entity_extractor.py`: extracts structured entities such as vocabulary, phrases, corrected terms, and cultural concepts
- `hearing.py`: normalizes STT output into a trusted “hearing result” for downstream orchestration
- `heritage_prompt.py`: generates targeted prompts for heritage/dialect/register collection
- `input_understanding.py`: merges hearing, interpretation, and optional audio understanding into one turn-understanding object
- `intent_classifier.py`: assigns primary/secondary intent labels with confidence
- `keyterm_service.py`: prepares session-aware keyterms for transcript repair, extraction boosting, and memory-aware focus
- `learning.py`: runs the background learning worker and processes queued learning signals
- `llm.py`: streams token deltas from an OpenAI-compatible local/remote LLM endpoint
- `memory_service.py`: manages hot session memory and durable cross-session memory snapshots
- `message_store.py`: provides helpers around session message/turn indexing and persistence support
- `personality.py`: plans LIPI’s character/tone/personality behavior deterministically
- `phrase_generator.py`: auto-generates phrase inventory when supply is low
- `phrase_pipeline.py`: selects which phrase a user should record next and manages phrase-lab flow
- `points.py`: calculates/logs points and rebuilds teacher summaries
- `post_generation_guard.py`: filters weak, repetitive, language-misaligned, or low-quality responses after generation
- `prompt_builder.py`: builds system prompts and teacher profile/register-aware guidance
- `response_cleanup.py`: trims/normalizes generated text for readable delivery and TTS safety
- `response_orchestrator.py`: assembles the live turn response from the various understanding/policy components
- `routing_hooks.py`: provides future-facing routing/adapter hooks for voice/model/profile selection
- `speaker_clustering.py`: clusters speaker embeddings incrementally
- `speaker_embeddings.py`: extracts and stores speaker embeddings asynchronously
- `stt.py`: handles Groq Whisper fallback speech-to-text behavior
- `teacher_modeling.py`: builds a structured model of teacher style, confidence, register, and behavior patterns
- `topic_memory.py`: stores lightweight session continuity and follow-up context
- `training_capture.py`: builds structured training-data envelopes from each turn
- `transcript_repair.py`: repairs low-confidence transcripts using prepared keyterm context
- `tts.py`: calls the ML TTS service, cleans text for speech, and routes by language
- `turn_intelligence.py`: computes/persists intent, entities, keyterms, code-switching, transcript repair, and learning quality
- `turn_interpreter.py`: infers social/teaching intent, correction status, topic, and follow-up zones from a hearing result
- `__init__.py`: package marker

### Backend tests (`backend/tests/`)

- `conftest.py`: shared test fixtures
- `test_admin_control.py`: control/moderation/admin flows
- `test_auth.py`: authentication behavior
- `test_health.py`: health endpoint/system status
- `test_hybrid_pivot.py`: hybrid/audio-understanding behavior
- `test_intelligence_layer.py`: intelligence-layer behavior expectations
- `test_learning.py`: learning pipeline behavior
- `test_learning_activation.py`: activation of durable learning paths
- `test_phrase_lab.py`: phrase lab behavior
- `test_points.py`: points and summary logic
- `test_services_llm.py`: LLM service integration behavior
- `test_services_stt_tts.py`: STT/TTS service wrappers
- `test_sessions_ws.py`: WebSocket conversation behavior
- `test_speaker_embeddings.py`: speaker embedding logic
- `test_turn_intelligence.py`: intent/entity/keyterm turn intelligence behavior
- `__init__.py`: package marker

### Alembic migrations and schema changes

Migration history in `backend/alembic/versions/`:

- `91ba4c4fe766_initial_schema.py`
  - baseline stamp only, no operations
  - marks transition away from ad hoc schema creation

- `f1c2d8b44a11_training_data_capture_signals.py`
  - adds training-capture signal columns to `messages`
  - supports raw/derived/high-value/style/prosody/nuance storage

- `a7c6e1d9f210_phrase_lab_and_review_queue.py`
  - adds review queue support
  - adds phrase generation, phrase catalog, phrase submissions, reconfirmation, skip, and metrics tables
  - adds source audio + approval fields to corrections/usage rules

- `b8d7e4c3f920_heritage_sessions.py`
  - adds `heritage_sessions`

- `d1e2f3a4b5c6_vocabulary_reliability.py`
  - adds vocabulary reliability/admin approval fields and related indexes

- `d3f4c6b8a921_curriculum_and_diversity_engine.py`
  - adds curriculum profile, topic coverage, global coverage, and prompt event tables

- `e4b7f9a21c10_intelligence_layer_core.py`
  - adds core intelligence-layer tables such as corrections, signals, memory, usage rules, and credibility history

- `e6f7a8b9c0d1_admin_queue_claims_and_metrics.py`
  - extends moderation queue with claim ownership/expiry support and admin-control operational metrics structures

- `f2a3b4c5d6e7_turn_intelligence_layer.py`
  - adds normalized turn intelligence persistence (`message_analysis`, `message_entities`) and supporting keyterm/intelligence schema

### Backend observations

- `backend/main.py` imports both product and admin route groups, making the backend the shared system-of-record/API for both public and control apps.
- The conversation stack is unusually deep for a small product repo; it behaves more like an orchestration engine than a thin API.
- There is still coexistence between old schema-creation approaches (`init-db.sql`, `db/init_db.py`) and Alembic, but migrations are now the intended path forward.

---

## 5) Frontend Deep Dive

The public frontend is a Next.js 14 App Router app focused on mobile-first teaching interactions, onboarding, and guided capture.

### Key frontend files

- `frontend/package.json`: scripts/dependencies
- `frontend/next.config.mjs`: standalone output, PWA setup, server action allowed origins
- `frontend/capacitor.config.ts`: Android wrapper config
- `frontend/Dockerfile`: frontend container build
- `frontend/jest.config.js`, `frontend/jest.setup.ts`: test setup
- `frontend/tsconfig.json`: TS config

### Libraries from `frontend/package.json`

Dependencies:

- `next`
- `react`
- `react-dom`
- `next-pwa`
- `@capacitor/core`
- `@capacitor/cli`
- `@capacitor/android`

Dev dependencies:

- TypeScript
- ESLint + `eslint-config-next`
- Jest
- Testing Library packages
- `@capacitor/assets`

### App structure (`frontend/app/`)

#### Root

- `app/layout.tsx`: global metadata, theme restore, PWA registration rules, `ThemeProvider`
- `app/page.tsx`: bilingual landing page
- `app/error.tsx`: app-level error boundary page
- `app/globals.css`: global theme/design tokens/styles

#### Auth / onboarding

- `app/auth/page.tsx`: Google OAuth + demo login screen with branded orb UI
- `app/onboarding/page.tsx`: multi-step profile/language/demographic onboarding
- `app/(auth)/auth.module.css`, `app/auth/auth.module.css`, onboarding styles: auth/onboarding styling

#### Tabbed user experience

- `app/(tabs)/layout.tsx`: tab-shell layout
- `app/(tabs)/home/page.tsx`: main home/dashboard entry
- `app/(tabs)/teach/page.tsx`: live teacher/LIPI conversation screen
- `app/(tabs)/phrase-lab/page.tsx`: phrase recording workflow
- `app/(tabs)/heritage/page.tsx`: heritage contribution flow
- `app/(tabs)/ranks/page.tsx`: leaderboard/rank view
- `app/(tabs)/settings/page.tsx`: settings/profile area
- `app/(tabs)/settings/dashboard/page.tsx`: dashboard subpage under settings

#### API route proxies / server routes

- `app/api/auth/demo/route.ts`: demo auth helper
- `app/api/auth/google/route.ts`: code exchange helper
- `app/api/auth/ws-token/route.ts`: short-lived WebSocket token helper
- `app/api/proxy/[...path]/route.ts`: backend proxy path
- `app/api/sessions/route.ts`: session creation passthrough
- `app/api/phrases/*`: phrase lab proxy routes
- `app/api/heritage/[...path]/route.ts`: heritage proxy routes

### Components

- `components/orb/Orb.tsx`: central branded visual/orb component
- `components/phrase-lab/HoldToRecordButton.tsx`: record interaction
- `components/phrase-lab/PhraseCard.tsx`: phrase display card
- `components/phrase-lab/VariationPrompt.tsx`: variation-capture UI
- `components/theme/ThemeProvider.tsx`: theme persistence/provider
- `components/ui/BottomNav.tsx`: mobile bottom navigation
- `components/ui/LipiPrimitives.tsx`: reusable UI primitives

### Frontend utility libs

- `lib/api.ts`: browser API client for auth, onboarding, sessions, leaderboard, dashboard
- `lib/backend-url.ts`: backend URL helpers
- `lib/websocket.ts`: WebSocket client wrapper using short-lived WS token handshake

### Public assets and PWA

- `public/manifest.webmanifest`
- `public/sw.js`, `public/workbox-*.js`
- app icons under `public/icons/`
- custom audio worker under `public/workers/vocal-processor.js`

### Testing

- `__tests__/api.test.ts`
- `__tests__/auth-page.test.tsx`
- `__tests__/orb.test.tsx`
- `__tests__/websocket.test.ts`

### Frontend behavior notes

- Uses HTTP-only cookie-based auth flows for safer token handling
- WebSocket connection is established after fetching a short-lived token
- PWA is disabled outside production or when `DISABLE_PWA=1`
- App is mobile-centric and includes Capacitor Android integration

---

## 6) Frontend-Control

### What it is

`frontend-control` is a separate internal administrative dashboard for moderation, analytics, exports, health, and audit operations. It is not the public teaching product; it is an enterprise/internal operations console.

### How it differs from `frontend`

| Area | `frontend` | `frontend-control` |
|---|---|---|
| Audience | public teachers/contributors | internal staff/admins |
| Purpose | conversation, onboarding, data contribution | moderation, curation, analytics, exports, ops |
| Stack version | Next 14 + React 18 | Next 16 + React 19 |
| Styling | custom CSS/CSS Modules | Tailwind CSS 4 |
| Auth style | user cookies / WS token flow | admin bearer token in cookie/localStorage |
| Key interactions | teach, phrase lab, heritage | queue claim/review, gold labeling, snapshots, health |

### Structure

- `src/app/layout.tsx`: wraps app in `AuthProvider`
- `src/app/page.tsx`: redirects to dashboard or login
- `src/app/login/page.tsx`: admin login/demo mode
- `src/app/(dashboard)/layout.tsx`: authenticated dashboard shell
- `src/app/(dashboard)/dashboard/page.tsx`: analytics overview
- `src/app/(dashboard)/moderation/page.tsx`: moderation queue and batch actions
- `src/app/(dashboard)/gold-records/page.tsx`: gold record browsing
- `src/app/(dashboard)/exports/page.tsx`: dataset export management
- `src/app/(dashboard)/health/page.tsx`: system health
- `src/app/(dashboard)/audit/page.tsx`: audit log browsing

### Support code

- `src/components/layout/Sidebar.tsx`: nav shell for dashboard sections
- `src/components/analytics/AnalyticsCharts.tsx`: charts for analytics views
- `src/components/dashboard/DashboardFilters.tsx`: dashboard filters
- `src/components/moderation/AudioWaveform.tsx`: waveform playback/inspection
- `src/context/AuthContext.tsx`: client auth state
- `src/lib/api.ts`: axios instance attaching `ctrl_token`

### Important notes

- `frontend-control/AGENTS.md` warns that this Next.js version may differ from older expectations.
- The included `README.md` is generic scaffold text and not a project-specific guide.
- There are existing uncommitted edits in `frontend-control/src/app/(dashboard)/dashboard/page.tsx` and `frontend-control/src/app/login/page.tsx` in the working tree; this mapping did not modify them.

---

## 7) ML Module

The `ml/` directory is a standalone FastAPI service for speech and voice workloads.

### Files

- `ml/main.py`: service entrypoint, startup model loading, `/health`, `/stt`, `/tts`, `/speaker-embed`, `/models/info`
- `ml/stt.py`: faster-whisper `large-v3` transcription service with VAD, prompt/language hinting, silence handling
- `ml/tts.py`: provider router choosing Coqui XTTSv2 primary and Piper fallback
- `ml/tts_provider.py`: provider interface/base abstraction
- `ml/tts_coqui.py`: Coqui XTTSv2 implementation
- `ml/tts_piper.py`: Piper implementation
- `ml/speaker_embed.py`: speaker embedding extraction service
- `ml/requirements.txt`: ML dependencies
- `ml/Dockerfile`: CUDA-based container image

### Runtime behavior

- Models load eagerly at startup
- STT and TTS are considered required for healthy service startup
- speaker embeddings are optional/degraded
- `/health` reports loaded/unloaded model status and CUDA visibility
- `/models/info` exposes effective TTS provider and model settings

### Model/tool choices visible in code

- STT: `faster-whisper large-v3`
- TTS: Coqui XTTSv2 primary, Piper fallback
- Speaker embeddings: custom `acoustic_signature_v1` style service

### Deployment characteristics

- Docker image is based on `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04`
- healthcheck hits `http://localhost:5001/health`
- designed for GPU-backed deployment

---

## 8) Monitoring

`monitoring/` currently contains:

- `monitoring/prometheus.yml`

### What it does

Prometheus is configured to scrape:

- `backend:8000/metrics`
- `ml:5001/metrics`
- `vllm:8080/metrics`
- Prometheus self-monitoring

### Notes

- Compose files include Prometheus and Grafana under a `monitoring` profile
- PostgreSQL exporter is mentioned as a future/optional sidecar but is not enabled in the current config
- The presence of monitoring config is ahead of actual application metrics instrumentation in some areas; it is infrastructure-ready more than fully observability-complete

---

## 9) Scripts

### Root-level utility scripts

- `copy_to_remote.sh`: remote copy helper
- `START_DEVELOPMENT.sh`: local development startup helper
- `gemma_proxy.py`: OpenAI-style proxy/shim helper for Gemma

### `scripts/` directory

- `scripts/deploy.sh`
  - production deployment/update workflow
  - intended for remote server rollout

- `scripts/gemma_openai_server.py`
  - OpenAI-compatible wrapper/server around Gemma model serving

- `scripts/server-health-check.sh`
  - broad server health script checking GPU, Docker, containers, service HTTP health, DB/cache/storage, disk, firewall, certificates, and recent errors

- `scripts/server-setup.sh`
  - fresh Ubuntu server bootstrap
  - installs NVIDIA drivers, Docker, nvidia-container-toolkit, firewall rules, sysctl tuning, deploy user, and repo clone

### General script pattern

The scripts assume a serious remote deployment target with GPUs, Dockerized infrastructure, and reproducible operational steps rather than a purely local toy setup.

---

## 10) Infrastructure

### Docker setup

#### `docker-compose.yml`

Main full-stack/dev-hybrid compose:

- `frontend`
- `backend`
- `postgres`
- `valkey`
- `minio`
- `minio-init`
- `prometheus` (monitoring profile)
- `grafana` (monitoring profile)

It also documents remote-only ML/vLLM paths in comments and includes environment wiring for frontend/backend.

#### `docker-compose.dev.yml`

Dev override:

- hot-reload backend mount
- direct port exposure for Postgres/Valkey/MinIO/backend
- disables GPU services locally through profiles

#### `docker-compose.remote.yml`

Remote full-GPU stack:

- `backend`
- `ml`
- `vllm`
- `postgres`
- `valkey`
- `minio`

This is the clearest “all-in-one remote production/inference” compose file.

### Caddy

`Caddyfile` provides:

- site domain binding via env
- reverse proxy to `frontend`
- `/api/*` to backend
- `/ws/*` to backend
- `/audio/*` to MinIO
- security headers
- compression
- MinIO console subdomain proxy

### Environment config

`.env.example` defines config for:

- app identity and URLs
- PostgreSQL
- Valkey
- turn intelligence / keyterm / transcript repair thresholds
- MinIO buckets
- vLLM
- ML service
- Groq fallback
- auth/Google OAuth
- frontend URLs
- backend host/port/JWT settings
- GPU settings
- TTS provider selection and voices
- monitoring ports/password
- Caddy domain/email

### Dockerfiles

- `backend/Dockerfile`: Python 3.11 slim backend image
- `ml/Dockerfile`: CUDA runtime image with Python 3.11, ffmpeg, libs for audio inference
- `frontend/Dockerfile`: public app image (present in repo)

### Makefile

Provides commands for:

- `make dev`
- `make prod`
- `make monitoring`
- `make down`
- `make logs`
- `make build`
- `make health`
- `make db-shell`
- `make valkey-shell`
- `make deploy`
- `make server-health`
- `make reset-db`

### Infra observations

- The repo currently contains multiple deployment stories:
  - local dev without GPU
  - remote GPU server with separate ML/vLLM
  - full compose-driven remote stack
- Docs mention Gemma 4 heavily, while compose files still include Qwen-oriented vLLM examples in some places; this suggests an evolving inference strategy.

---

## 11) Key Documentation

### Root markdown files and their purpose

- `5_STEP_LEARNING_CYCLE.md`: describes the observation-to-storage learning loop
- `API_COMPARISON.md`: compares fallback API options, cost, and tradeoffs
- `CLAUDE.md`: engineering master brief / project north-star doc
- `CRITICAL_CHALLENGES.md`: major implementation/product problems and risks
- `DATABASE_SCHEMA.md`: schema reference across main tables
- `DECISION_CHECKLIST.md`: architectural and implementation decision checklist
- `DEV_ONBOARDING.md`: developer setup, architecture, codebase map, workflow
- `DOCUMENTATION_INDEX.md`: central index of repo documentation
- `GAMIFICATION_DATA_MODEL.md`: points/badges/leaderboard design
- `HANDOVER_TO_CODEX.md`: current-state handoff snapshot for next engineer
- `LIPI_PHILOSOPHY.md`: product philosophy and student-teacher framing
- `LLM_BENCHMARK_PLAN.md`: evaluation plan for LLM selection/quality
- `LLM_SELECTION.md`: rationale behind chosen/favored LLM path
- `OPERATIONS.md`: runbook for running and operating the system
- `PERFORMANCE_TARGETS.md`: latency/SLO/performance expectations
- `PHASE_ROADMAP.md`: product roadmap and phase tracking
- `PHRASE_LAB.md`: phrase-lab-specific module/design document
- `README.md`: highest-level repo overview and current state
- `RELEASE_v1.md`: stable v1 release reference
- `STABILITY_REPORT.md`: stability/readiness/risk report
- `STT_ARCHITECTURE.md`: speech-recognition architecture and quality strategy
- `STUDENT_CHARACTER_DESIGN.md`: LIPI’s persona/character definition
- `SYSTEM_ARCHITECTURE.md`: macro architecture/system design
- `SYSTEM_PROMPTS.md`: prompt/system behavior design
- `SYSTEM_STATUS_REPORT.md`: latest comprehensive health/status report
- `TTS_ARCHITECTURE.md`: speech synthesis/voice routing architecture
- `UI_UX_DESIGN.md`: public UI/UX design reference
- `VOICE_TRAINING_PIPELINE.md`: custom voice training/fine-tuning direction

### Documentation quality observations

- Documentation coverage is unusually extensive and acts as a second source of truth beside code.
- Some docs are canonical and current; some deployment/model-selection docs reflect older infrastructure snapshots.
- `DOCUMENTATION_INDEX.md` is helpful and mostly consistent with the repo’s current doc surface.

---

## 12) Database Schema

The database is PostgreSQL-backed and spans user/product state, learning signals, moderation, gold curation, and analytics support.

### Core entity groups

#### Identity and teaching sessions

- `users`
- `teaching_sessions`
- `messages`

Relationships:

- one `User` -> many `TeachingSession`
- one `User` -> many `Message`
- one `TeachingSession` -> many `Message`

#### Gamification

- `points_transactions`
- `teacher_points_summary`
- `badges`
- `teacher_badges`

Relationships:

- one `User` -> many `PointsTransaction`
- one `User` -> one `TeacherPointsSummary`
- many-to-many-ish between `User` and `Badge` through `TeacherBadge`

#### Curriculum / coverage

- `user_curriculum_profiles`
- `user_topic_coverage`
- `global_language_coverage`
- `curriculum_prompt_events`

Relationships:

- `user_curriculum_profiles.user_id` -> `users.id`
- `user_topic_coverage.user_id` -> `users.id`
- `curriculum_prompt_events.user_id` -> `users.id`
- `curriculum_prompt_events.session_id` -> `teaching_sessions.id`

#### Intelligence / learning state

From `models/intelligence.py`, key tables include:

- `correction_events`
- `session_memory_snapshots`
- `teacher_signals`
- `teacher_credibility_events`
- `knowledge_confidence_history`
- `usage_rules`
- `message_analysis`
- `message_entities`
- `admin_keyterm_seeds`
- `review_queue_items`
- `vocabulary_entries`
- `vocabulary_teachers`

Likely relationships:

- `correction_events` reference sessions/users/messages
- `message_analysis` references `messages`
- `message_entities` reference `message_analysis` or `messages` depending persistence structure
- `review_queue_items` reference `users`, `teaching_sessions`, and may be derived from corrections/extractions
- `usage_rules` and vocabulary tables tie durable learning back to teachers and sessions
- `session_memory_snapshots` tie persistent memory to a teacher/session timeline

#### Phrase Lab

- `phrase_generation_batches`
- `phrases`
- `phrase_submission_groups`
- `phrase_submissions`
- `phrase_skip_events`
- `phrase_reconfirmation_queue`
- `phrase_metrics`

Relationships:

- one generation batch -> many phrases
- one phrase -> many submission groups/submissions/skip events
- one user -> many phrase submissions/groups/skips
- one group -> many submissions

#### Heritage

- `heritage_sessions`

Relationship:

- one `User` -> many `HeritageSession`

#### Admin / gold curation

- `admin_accounts`
- `admin_audit_logs`
- `dataset_gold_records`
- `dataset_snapshots`

Relationships:

- one `AdminAccount` -> many `AdminAuditLog`
- `GoldRecord` optionally references original `Message`, `TeachingSession`, `User`, and labeling admin
- `DatasetSnapshot` references creating admin

### Most important schema pattern

The schema is layered:

1. **raw interaction data** (`messages`, audio paths, sessions)
2. **derived intelligence** (`message_analysis`, `message_entities`, teacher signals, corrections)
3. **durable learning state** (`usage_rules`, memory snapshots, vocabulary tables)
4. **human review and gold curation** (`review_queue_items`, `dataset_gold_records`, `dataset_snapshots`)

That layering is the clearest architectural signature of the project.

---

## 13) Current Status / Observations

### Major strengths

- Strong product philosophy is consistently reflected in code and docs.
- The repo already spans product, ML, moderation, and infra rather than being a partial prototype.
- The backend has a clear internal service decomposition for turn processing.
- The moderation/gold pipeline is not superficial; it includes review queues, claims, audit logging, and export packaging.
- Phrase Lab and Heritage broaden the collection strategy beyond open conversation.

### Important gaps / inconsistencies

- **Inference strategy drift**: docs emphasize Gemma 4/Gemma proxying, while several compose files still show Qwen/vLLM examples; the operational reality should be standardized.
- **Schema management overlap**: Alembic is clearly the intended future path, but `init-db.sql` and `db/init_db.py` still coexist.
- **Frontend-control docs**: the control app README is generic scaffold text and does not document the actual dashboard.
- **Generated/build artifacts in repo tree**: there are checked-in/generated directories like `.next`, Android build outputs, node_modules references in scans, and local logs; these make repo mapping noisier and suggest cleanup opportunities.
- **Monitoring is infra-ready but instrumentation maturity is unclear**: Prometheus targets exist, but not all services necessarily expose full useful metrics today.

### Notable patterns

- Public app and control app are intentionally split rather than role-gated within one frontend.
- The backend treats learning as a pipeline with confidence, review, and approval gating rather than blindly trusting extracted signals.
- Low-confidence and low-trust signals are routed toward moderation/review rather than direct training.
- Cross-session memory and approved usage rules are re-injected into later turns, making the product behave more like a persistent learner.

### Likely active priorities based on code/docs

- improve STT robustness for Nepali/mixed turns
- improve TTS voice quality/routing
- improve conversational naturalness/tone
- increase reliability of entity/intent/keyterm intelligence
- expand high-quality gold curation throughput

### Extra repo content worth noting

- `LIPI/` appears to contain design/prototype artifacts (`app.jsx`, `screens.jsx`, `theme.jsx`, etc.) separate from the main shipping frontends.
- The working tree already has local modifications in:
  - `backend/routes/auth.py`
  - `frontend-control/src/app/(dashboard)/dashboard/page.tsx`
  - `frontend-control/src/app/login/page.tsx`
  These were present before creation of this map.

---

## Appendix A: Directory Summary

### Root

- repo docs and operational files
- compose/env/Caddy/Makefile
- top-level helper scripts

### `backend/`

- FastAPI app, services, models, migrations, tests

### `frontend/`

- public teacher-facing Next.js app + Android wrapper

### `frontend-control/`

- admin/moderation analytics dashboard

### `ml/`

- FastAPI STT/TTS/speaker embedding microservice

### `monitoring/`

- Prometheus configuration

### `scripts/`

- deploy/setup/health-check/model-server scripts

### `LIPI/`

- separate prototype/design artifacts not wired into the main production apps

---

## Appendix B: Quick “Start Reading Here” File List

For fast orientation, start with:

1. `README.md`
2. `DEV_ONBOARDING.md`
3. `SYSTEM_ARCHITECTURE.md`
4. `backend/main.py`
5. `backend/routes/sessions.py`
6. `backend/models/intelligence.py`
7. `frontend/app/(tabs)/teach/page.tsx`
8. `frontend-control/src/app/(dashboard)/moderation/page.tsx`
9. `ml/main.py`
10. `docker-compose.yml`
