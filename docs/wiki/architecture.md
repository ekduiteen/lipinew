# Architecture

## Component Diagram

```text
Teacher
  |
  v
frontend (Next.js public app)
  |-- REST through Next proxy -> backend /api/*
  |-- WebSocket direct -------> backend /ws/session/{session_id}
  |
  v
backend (FastAPI)
  |-- async SQLAlchemy -> Postgres
  |-- cache/queues ----> Valkey
  |-- audio/archive ---> MinIO
  |-- STT/TTS/embed ---> ML service
  |-- generation ------> vLLM/OpenAI-compatible endpoint
  |
  v
derived data: messages, signals, corrections, review queue, gold records, exports

Internal reviewer
  |
  v
frontend-control (Next.js admin app)
  |
  v
backend /api/ctrl/*
```

## Boundaries

The public frontend should stay focused on teacher experience and local browser/media concerns. It should not own learning rules, moderation decisions, or durable business logic.

The backend owns product state, learning state, security, moderation, analytics, export rules, and service orchestration.

The ML service owns heavy audio/model execution and exposes small HTTP endpoints. Backend services decide how and when to call it.

The control dashboard owns internal operator UX. It consumes `/api/ctrl/*` endpoints and should not bypass backend authorization or audit behavior.

## Persistent State

Postgres stores durable truth:

- users and teaching sessions
- messages and message-level intelligence
- points/badges
- vocabulary and usage rules
- curriculum coverage
- review queue and gold records
- admin accounts/audit logs
- dataset snapshots/exports

Valkey stores transient and queue state:

- session message history
- tone/profile cache
- learning queue states
- worker processing/dead-letter states
- fast leaderboard/summary caches where used

MinIO stores large binary artifacts:

- teacher audio
- generated TTS
- export archives

## Startup Lifecycle

`backend/main.py`:

- validates `JWT_SECRET`
- optionally runs Alembic migrations
- checks Valkey
- creates shared `httpx.AsyncClient`
- starts background loops for point summaries, learning worker, and phrase generation
- registers public and admin routers

`ml/main.py`:

- eager-loads STT model
- eager-loads TTS provider/fallback
- tries speaker embedding service
- fails startup if STT or TTS cannot load
- reports degraded health if speaker embeddings are unavailable

## Primary Runtime Flow

1. Public frontend authenticates and stores httpOnly cookies through Next.js route proxies.
2. Frontend creates a session through `/api/sessions`.
3. Frontend obtains a short-lived WebSocket token through `/api/auth/ws-token`.
4. WebSocket sends binary audio frames directly to backend.
5. Backend transcribes audio via ML service.
6. Backend enriches the turn using memory, policy, curriculum, keyterms, and intelligence services.
7. Backend streams LLM tokens and sends TTS audio.
8. Backend persists teacher and assistant messages.
9. Backend queues learning/training capture work.
10. Moderation/admin systems later approve, reject, or export derived records.

See [Conversation Flow](conversation-flow.md) for the turn-level detail.

