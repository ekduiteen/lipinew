# LIPI — Developer Onboarding Guide

> **Living document. Update rule: every PR that adds a service, endpoint, pattern, or architectural decision MUST include a corresponding update to this file. No exceptions. If you shipped it and didn't document it here, it didn't happen.**
> Last synced: 2026-04-15 — Added durable Valkey learning queue, switched TTS docs to OmniVoice, documented single-L40S remote layout, and clarified the current frontend testing caveat around `localhost:8000`.

---

## 1. What You're Building (Read This First)

LIPI is **not** a chatbot. LIPI is a **community data-collection platform disguised as a conversation.**

| Role | Entity | What they do |
|------|--------|--------------|
| Student | LIPI (the AI) | Asks questions, makes mistakes, accepts corrections |
| Teacher | The user | Speaks, corrects, teaches — unknowingly donating language data |

Every conversation is structured data collection. The student–teacher dynamic is the data strategy. Monthly LoRA fine-tuning on that data is the product flywheel.

**If a feature doesn't serve data collection or teacher retention, it doesn't ship.**

---

## 2. Codebase Map (Current State)

```
lipi/
├── CLAUDE.md                   ← Engineering source of truth. Read before coding.
├── PHASE_ROADMAP.md            ← 16-week delivery roadmap
├── DEV_ONBOARDING.md           ← you are here
├── README_DEV.md               ← local setup quick-start
├── docker-compose.yml          ← full stack definition
├── Caddyfile                   ← reverse proxy config
├── .env.example                ← all env vars with comments
├── init-db.sql                 ← PostgreSQL schema + pgvector + badge seed
│
├── ml/                         ← GPU microservice (STT + TTS)
│   ├── main.py                 ← FastAPI app, /health /stt /tts /models/info
│   ├── stt.py                  ← STTService (faster-whisper large-v3)
│   ├── tts.py                  ← TTSService (OmniVoice)
│   ├── requirements.txt
│   └── Dockerfile
│
├── backend/                    ← FastAPI REST + WebSocket
│   ├── main.py                 ← app factory, lifespan, routes, 5-min summary task
│   ├── config.py               ← all settings from env (pydantic-settings)
│   ├── cache.py                ← Valkey async client (NOT redis)
│   ├── dependencies/
│   │   └── auth.py             ← get_current_user (Bearer JWT), get_ws_user (query param)
│   ├── models/                 ← SQLAlchemy 2.0 ORM
│   │   ├── user.py             ← User
│   │   ├── session.py          ← TeachingSession
│   │   ├── points.py           ← PointsTransaction, TeacherPointsSummary
│   │   ├── badge.py            ← Badge, TeacherBadge
│   │   └── message.py          ← Message (permanent per-turn DB record)
│   ├── db/
│   │   └── connection.py       ← async engine + get_db dependency
│   ├── routes/
│   │   ├── auth.py             ← POST /api/auth/google, /api/auth/refresh
│   │   ├── sessions.py         ← POST /api/sessions + WS /ws/session/{id}
│   │   ├── leaderboard.py      ← GET /api/leaderboard?period=weekly|monthly|all_time
│   │   └── teachers.py         ← POST /api/teachers/onboarding (JWT), GET /me/stats, GET /me/badges
│   └── services/
│       ├── prompt_builder.py   ← build_system_prompt(TeacherProfile) → str
│       ├── llm.py              ← vLLM streaming + Groq fallback
│       ├── stt.py              ← HTTP client to ml:5001/stt + Groq fallback
│       ├── tts.py              ← HTTP client to ml:5001/tts + silence fallback
│       ├── points.py           ← calculate_points, log_transaction, rebuild_summary
│       ├── badges.py           ← check_and_award (idempotent)
│       ├── message_store.py    ← persist_teacher_turn, persist_lipi_turn (permanent DB)
│       └── learning.py         ← OBSERVE→EXTRACT→STORE vocabulary cycle (background task)
│
├── frontend/                   ← Next.js 14 PWA (App Router)
│   ├── app/
│   │   ├── layout.tsx          ← ThemeProvider wraps everything
│   │   ├── globals.css         ← CSS variables for all 4 themes
│   │   ├── page.tsx            ← Landing page (bilingual)
│   │   ├── (auth)/page.tsx     ← Google OAuth screen
│   │   ├── onboarding/page.tsx ← 7-question bilingual onboarding
│   │   └── (tabs)/             ← Tab layout with BottomNav
│   │       ├── layout.tsx
│   │       ├── home/page.tsx   ← Stats + CTA + mini-leaderboard
│   │       ├── teach/page.tsx  ← Orb + VAD + WebSocket conversation
│   │       ├── ranks/page.tsx  ← Weekly/monthly/all-time leaderboard
│   │       └── settings/page.tsx ← Theme picker with live Orb previews
│   ├── components/
│   │   ├── orb/Orb.tsx         ← 4-state animated orb (idle/listening/thinking/speaking)
│   │   ├── theme/ThemeProvider.tsx ← data-theme on <html>, localStorage persist
│   │   └── ui/BottomNav.tsx    ← 4-tab nav, bilingual labels
│   └── lib/
│       ├── api.ts              ← REST client (all /api/* calls)
│       └── websocket.ts        ← LipiWebSocket class (binary + JSON frames)
│
└── pipeline/                   ← Monthly LoRA fine-tuning (not yet built)
    ├── prepare_data.py
    ├── train_lora.py
    ├── eval.py
    └── announce.py
```

---

## 3. Hardware & GPU Allocation

```
Server:  Own bare-metal, Ubuntu 22.04, CUDA 12.1
RAM:     256 GB
Storage: 4 TB NVMe
GPUs:    1× NVIDIA L40S (48 GB VRAM)

GPU 0:  Host-level vLLM (Qwen2.5-14B-Instruct-AWQ on :8100)
        + remote ML container (faster-whisper large-v3 on :5001)
        + no dedicated GPU left for compose-managed vLLM duplication
```

> **Current live deployment note (2026-04-14):** the remote server currently has a single L40S, not two. The stable production-like layout is:
> - host-level `vLLM` on `127.0.0.1:8100`
> - Docker `backend`, `ml`, `postgres`, `valkey`, `minio`
> - Docker backend reaches host `vLLM` via `http://host.docker.internal:8100`
> - compose-managed `vllm` should stay disabled on this host to avoid GPU memory contention
>
> `PHASE_ROADMAP.md` still references future multi-GPU expansion. Do not assume the current remote box has 2 GPUs.

---

## 4. Stack Reference (Locked — Do Not Substitute)

| Layer | Tech | Key constraint |
|-------|------|----------------|
| Frontend | Next.js 14, TypeScript | App Router only, Server Components default |
| Backend | FastAPI, Python 3.11 | async everywhere, httpx not requests |
| LLM inference | vLLM (OpenAI-compat) | Groq fires only on local failure |
| LLM model | Qwen3-32B | fits 2× L40S at float16 |
| STT | faster-whisper large-v3 | VAD built-in, no hold-to-talk |
| TTS | OmniVoice | Zero-shot multilingual TTS with optional voice cloning |
| Database | PostgreSQL 16 + pgvector | speaker embeddings as vector(512) |
| Cache | **Valkey** (BSD-3) | **NEVER** `from redis import …` |
| Object storage | MinIO | S3-compat, self-hosted |
| Reverse proxy | **Caddy** | auto HTTPS, not nginx |
| Deployment | Coolify | self-hosted Vercel alternative |

> **Valkey vs Redis:** Redis switched to SSPL (non-OSS) in 7.x. Valkey is the BSD-3-licensed fork. Every import in this repo uses `from valkey.asyncio import Valkey`. If you see `from redis import …`, it's a bug.

---

## 5. Local Environment Setup

### 5.1 Prerequisites

```bash
# Required
docker --version          # 24+
docker compose version    # v2 (note: not docker-compose v1)
nvidia-smi                # driver 535+
nvidia-container-toolkit  # GPU passthrough to Docker
```

### 5.2 First run

```bash
cp .env.example .env
# Fill in: POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD, JWT_SECRET
# Optional for CPU-only: GROQ_API_KEY (enables fallback mode)

# Verify GPU passthrough
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi

# Start infra (fast, no GPU)
docker compose up -d postgres valkey minio minio-init

# Start GPU services (slow cold start: vLLM ~5 min, ml ~2 min)
docker compose up -d vllm ml

# Start app services
docker compose up -d backend frontend caddy
```

### 5.3 Verify everything is healthy

```bash
curl http://localhost:8000/health
# → {"status":"ok","database":true,"valkey":true,"vllm":true,"ml_service":true}

curl http://localhost:5001/health
# → {"status":"ok","stt_loaded":true,"tts_loaded":true,...}

curl http://localhost:8080/v1/models
# → {"data":[{"id":"lipi",...}]}
```

> **Current caveat (2026-04-15):** in the hybrid local-dev setup, `frontend/.env.local` points the browser app at `http://localhost:8000`, but the local Docker backend is not published to the host by default. If you run `npm run dev` locally without either:
> - publishing the backend on host `:8000`, or
> - recreating the SSH tunnel to the remote backend on local `:8000`
>
> the frontend will appear to hang or spin because its API target is unreachable or not the expected FastAPI service.

### 5.4 CPU-only mode (no GPUs)

Comment out `vllm` and `ml` services in `docker-compose.yml`. Set `GROQ_API_KEY` in `.env`. All STT/LLM/TTS calls will route to Groq. Useful for frontend development.

### 5.5 Hot reload (outside Docker)

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
# Runs on :3000, proxied through Caddy at :443

# ML service (GPU only)
cd ml && pip install -r requirements.txt
STT_DEVICE=cuda:0 TTS_DEVICE=cuda:1 uvicorn main:app --port 5001
```

Infra services (`postgres`, `valkey`, `minio`) must still be running in Docker.

### 5.6 Frontend testing on a laptop (current safest path)

```bash
# 1. Start a tunnel so the local frontend can reach the remote backend stack
ssh -N -p 41447 \
  -L 8000:localhost:8000 \
  -L 5001:localhost:5001 \
  -L 8100:localhost:8100 \
  -L 9000:localhost:9000 \
  ekduiteen@202.51.2.50

# 2. In a separate terminal, start the Next dev server
cd frontend && npm install && npm run dev

# 3. Verify the two ports independently
curl -I http://127.0.0.1:3000
curl http://127.0.0.1:8000/health
```

If `:3000` responds but the app still does not load data, check `:8000` first. A healthy HTML page on `:3000` with a broken or missing backend on `:8000` looks like a "frontend stuck loading" issue but is really an API routing problem.

---

## 6. Architecture: How a Conversation Turn Works

```
[Browser]
  │  audio (WebM/WAV binary frame)
  ▼
[Caddy :443]  /ws/session/{id}?token=<jwt>
  │
  ▼
[backend:8000]  routes/sessions.py
  │
  ├─ 0. get_ws_user(token) → user_id              JWT auth on connect
  │
  ├─ 1. stt_svc.transcribe(audio_bytes)           OBSERVE
  │     └─ POST ml:5001/stt  → {text, language, confidence, duration_ms}
  │           fallback: Groq Whisper API
  │
  ├─ 2. Register switch detection (e.g. "तिमी भनेर बोल")
  │     → rebuild system prompt if register changed
  │
  ├─ 3. llm_svc.generate(messages, stream=True)
  │     └─ POST vllm:8080/v1/chat/completions (SSE stream)
  │           fallback: Groq llama-3.3-70b
  │     → stream JSON {"type":"token","text":"..."} frames to client
  │
  ├─ 4. Persist both turns to DB                  STORE
  │     └─ message_store.persist_teacher_turn()
  │     └─ message_store.persist_lipi_turn()
  │     └─ Detect correction → log points_transaction
  │
  ├─ 5. learning_svc.enqueue_turn()
  │     ├─ PUSH: save extraction job to Valkey pending queue
  │     ├─ WORKER: backend lifespan task moves job → processing queue
  │     ├─ PROCESS: LLM extracts vocabulary JSON from teacher utterance
  │     ├─ EXTRACT: parse {word, language, definition_en}
  │     └─ STORE: upsert vocabulary_entries + vocabulary_teachers
  │               log word_learned (5pts) + pioneer_word (25pts) if first ever
  │        ← durable + retryable, never blocks the WS response
  │
  ├─ 6. tts_svc.synthesize(lipi_text)
  │     └─ POST ml:5001/tts  → WAV bytes
  │           fallback: 300ms silence (never stall the WS)
  │
  └─ 7. Send {"type":"tts_start"} → WAV binary → {"type":"tts_end"}

[Browser]
  ├─ Queues WAV frames → Web Audio API playback
  ├─ Orb state machine: idle → listening → thinking → speaking
  └─ Correction card slides up if is_correction=true (fades 3s)
```

### Fallback chain (circuit breaker)

```
vLLM available?  ──yes──► vLLM (primary)
     │ no
     ▼
Groq key set?    ──yes──► Groq API (fallback)
     │ no
     ▼
  raise 503
```

Same pattern for STT. TTS never raises — returns silence on failure.

---

## 7. Key Patterns & Conventions

### 7.1 Never import Redis

```python
# ✅ Correct
from valkey.asyncio import Valkey

# ❌ Wrong — will break in CI and violates license policy
from redis.asyncio import Redis
```

### 7.2 Dynamic system prompts — never static

```python
# ✅ Correct — fresh prompt each session from tone profile
system_prompt = build_system_prompt(profile)

# ❌ Wrong — static prompt ignores register, gender, phase
SYSTEM_PROMPT = "You are LIPI, a language learning student..."
```

### 7.3 Points are immutable

```python
# ✅ Correct — append only
await points_svc.log_transaction(db, user_id=..., event_type="correction_accepted")

# ❌ Wrong — never update or delete points rows
await db.execute(update(PointsTransaction).where(...).values(final_points=0))
```

### 7.4 All HTTP calls use httpx, never requests

```python
# ✅ Correct
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.post(...)

# ❌ Wrong — blocking in async context
import requests
resp = requests.post(...)
```

### 7.5 CSS variables for all colors — never hardcode

```tsx
// ✅ Correct
style={{ background: "var(--accent)" }}

// ❌ Wrong — breaks theme switching
style={{ background: "#6366f1" }}
```

### 7.6 Address registers

| Age range | Default register | Nepali address |
|-----------|-----------------|----------------|
| 60+ | हजुर (hajur) | दाइ/दिदी |
| 30–59 | तपाईं (tapai) | दाइ/दिदी |
| <30 | तिमी (timi) | भाइ/बहिनी |
| explicit | तँ (ta) | only if teacher requests |

The teacher can switch at any time with natural language: `"मलाई तिमी भनेर बोल"`. The WS handler detects this and rebuilds the system prompt mid-conversation.

---

## 7b. Authentication

### How JWT auth works

```
Browser                    Backend
  │  POST /api/auth/google   │
  │  { code, redirect_uri }  │
  │─────────────────────────►│
  │                          ├─ exchange code with Google
  │                          ├─ fetch userinfo (sub, email, name)
  │                          ├─ upsert User in DB
  │                          └─ create_access_token(user_id) → JWT
  │  { access_token }        │
  │◄─────────────────────────│
  │                          │
  │  store in localStorage("lipi.token")
  │
  │  GET /api/teachers/me/stats
  │  Authorization: Bearer <jwt>
  │─────────────────────────►│
  │                          ├─ get_current_user() decodes JWT → user_id
  │                          └─ serve stats
  │
  │  WS /ws/session/{id}?token=<jwt>
  │─────────────────────────►│
  │                          ├─ get_ws_user(token) decodes JWT → user_id
  │                          └─ conversation begins
```

### Dependencies (`backend/dependencies/auth.py`)

| Dependency | Use case |
|---|---|
| `get_current_user` | REST routes — reads `Authorization: Bearer <token>` header |
| `get_current_user_optional` | REST routes where auth is optional |
| `get_ws_user` | WebSocket — reads `?token=<jwt>` query param (browsers can't set WS headers) |

### Where each is used

| Route | Dependency |
|---|---|
| `GET /api/teachers/me/stats` | `get_current_user` |
| `GET /api/teachers/me/badges` | `get_current_user` |
| `POST /api/teachers/onboarding` | `get_current_user` (JWT Bearer) |
| `GET /api/leaderboard` | `get_current_user_optional` (public read) |
| `WS /ws/session/{id}` | `get_ws_user` |
| `POST /api/sessions` | `get_ws_user` (same pattern) |

---

## 7c. Learning Cycle (OBSERVE → PROCESS → EXTRACT → STORE)

This is the core product loop — how LIPI actually learns from teachers.

```
Teacher speaks
     │
     ▼
STT → {text, confidence, language, duration_ms}
     │
     ▼  OBSERVE
confidence >= 0.6 AND len(text) >= 3?
     │ yes
     ▼
     │  PROCESS
Learning job enqueued in Valkey (doesn't block WS):
     pending queue → processing queue → dead-letter on repeated failure
     │
     ▼  PROCESS
LLM extraction call (~200ms worker-side):
     prompt: "Extract vocabulary from: '{teacher_text}'"
     response: {"words": [{"word": "...", "language": "ne", "definition_en": "..."}]}
     │
     ▼  EXTRACT
Parse JSON → list of {word, language, definition_en}
     │
     ▼  STORE
For each word:
  ├─ NEW word?  → INSERT vocabulary_entries (pioneer_teacher_id = this user)
  │              → log pioneer_word (25 pts × streak multiplier)
  │              → INSERT vocabulary_teachers (contribution_type='first_teach')
  └─ KNOWN word? → UPDATE vocabulary_entries (times_taught++, confidence += 0.05)
                  → INSERT vocabulary_teachers (contribution_type='reinforcement')
                  → log word_learned (5 pts × streak multiplier)
```

**Key design decisions:**
- Extraction is queued in Valkey and consumed by a backend worker — never adds latency to the WS turn
- Low-confidence audio (< 0.6) is skipped — bad audio = bad data
- Max 5 words extracted per turn — prevents LLM hallucination floods
- `vocabulary_entries` has `UNIQUE(word, language)` — safe to upsert concurrently
- Pioneer status is set at insert time and never changes
- Failed jobs retry up to the configured max, then move to a dead-letter queue for inspection

---

## 8. Database Quick Reference

### Connect

```bash
docker compose exec postgres psql -U lipi -d lipi
```

### Key tables

| Table | Purpose |
|-------|---------|
| `users` | Teacher profiles, onboarding fields |
| `teacher_tone_profiles` | Register, energy, humor per teacher |
| `teaching_sessions` | Session metadata, phase, register used |
| `points_transactions` | **Immutable** event log (never UPDATE) |
| `teacher_points_summary` | Cached totals, rebuilt every 5 min |
| `badges` | Badge definitions (9 types, seeded) |
| `teacher_badges` | Many-to-many: which teacher earned which badge |
| `messages` | Per-turn message log |
| `vocabulary_entries` | Words LIPI has learned, with trigram index |
| `speaker_embeddings` | `vector(512)` with HNSW index for dialect clustering |

### Reset schema

```bash
docker compose down -v          # WARNING: drops all data
docker compose up -d postgres   # init-db.sql runs automatically
```

### Migrations

Numbered SQL files in `backend/db/migrations/`. Never `ALTER TABLE` in application code.

---

## 9. Frontend Quick Reference

### Theme system

Four themes controlled by `data-theme` attribute on `<html>`:
- `dark` (default) — deep space
- `bright` — light mode
- `cyberpunk` — neon green/pink on black
- `traditional` — amber/red on dark brown (opt-in)

`ThemeProvider` reads from `localStorage` on mount and sets the attribute. Every color in the app comes from `var(--bg)`, `var(--fg)`, `var(--accent)`, `var(--orb-a/b/c)` etc. Never hardcode hex values.

### Orb states

| State | When | Visual |
|-------|------|--------|
| `idle` | Waiting for voice | Slow breathing pulse |
| `listening` | VAD detects voice | Ripple rings expand outward |
| `thinking` | Audio sent, waiting for LLM | Gradient rotates |
| `speaking` | TTS audio playing | Canvas waveform rings |

State is managed in `app/(tabs)/teach/page.tsx` and passed as a prop to `<Orb state={orbState} />`.

### Bilingual rule

Every user-facing string has Nepali (primary, larger, top) and English (secondary, smaller, below). Never ship an English-only string. See `globals.css` for `.text-nepali` and `.text-latin` classes.

### Navigation

4 tabs: Home → `/home`, Teach → `/teach`, Ranks → `/ranks`, Settings → `/settings`. All live inside `app/(tabs)/` with a shared `layout.tsx` containing `<BottomNav>`.

---

## 10. Services Reference

### ML Service (`ml:5001`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Returns `{cuda_available, stt_loaded, tts_loaded, gpu_count}` |
| `/stt` | POST | `multipart/form-data` audio → `{text, language, confidence, duration_ms}` |
| `/tts` | POST | `{"text":"...", "language":"ne"}` → WAV bytes |
| `/models/info` | GET | Model names and devices |

**STT**: faster-whisper large-v3 with VAD filter. Auto-detects language (Nepali or English, per utterance).
**TTS**: OmniVoice. Returns float32 mono WAV at 24kHz.

**Current remote behavior (1-GPU host):**
- `stt_loaded=true` and usable
- `tts_loaded=false` on the remote server at the moment
- backend TTS path still works because `backend/services/tts.py` falls back to silence when `/tts` is unavailable

**OmniVoice integration notes:**
- `OMNIVOICE_MODE=auto` gives a model-chosen voice without a reference clip
- `OMNIVOICE_MODE=clone` requires both `OMNIVOICE_REF_AUDIO` and `OMNIVOICE_REF_TEXT`
- first rollout should validate plain synthesis first, then switch to clone mode once we have a canonical LIPI reference voice

### Backend (`backend:8000`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Checks db + valkey + vllm + ml |
| `/ws/session/{id}` | WS | Core conversation loop |
| `/api/auth/google` | POST | OAuth code → JWT |
| `/api/auth/refresh` | POST | Sliding JWT refresh |
| `/api/teachers/onboarding` | POST | Save onboarding fields + cache tone profile in Valkey (JWT required) |
| `/api/teachers/me/stats` | GET | Points, streak, rank |
| `/api/teachers/me/badges` | GET | Earned badges |
| `/api/leaderboard` | GET | `?period=weekly\|monthly\|all_time` (Valkey cached) |

### vLLM

OpenAI-compatible. The backend's `llm.py` calls `/v1/chat/completions` with `stream: true`.

**Current remote runtime:**
- host-level `vLLM` listens on `127.0.0.1:8100`
- model currently serving: `Qwen/Qwen2.5-14B-Instruct-AWQ`
- Docker backend uses `VLLM_URL=http://host.docker.internal:8100`
- compose-managed `vllm:8080` is intentionally not used on the single-L40S host

### Port Map (Current Remote + Tunnel Layout)

| Port | Location | Purpose |
|------|----------|---------|
| `41447` | remote host | SSH |
| `8000` | remote Docker + local tunnel | FastAPI backend for hybrid local frontend testing |
| `5001` | remote Docker + local tunnel | ML service |
| `8100` | remote host + local tunnel | host-level vLLM |
| `9000` | remote Docker + local tunnel | MinIO API |
| `9001` | remote Docker | MinIO console |
| `5432` | remote Docker internal only | PostgreSQL |
| `6379` | remote Docker internal only | Valkey |

**Local forwarded ports currently in use:**
- `127.0.0.1:8000` → remote backend, but only if the SSH tunnel is active
- `127.0.0.1:5001` → remote ML
- `127.0.0.1:8100` → remote host-level vLLM
- `127.0.0.1:9000` → remote MinIO
- `127.0.0.1:3000` should be kept free for local `next dev`; do not include it in the SSH tunnel unless you intentionally want a remote frontend

---

## 11. Points & Gamification

### Point values

| Event | Base points |
|-------|-------------|
| `session_base` | 10 |
| `word_learned` | 5 |
| `correction_accepted` | **15** (highest per-event value) |
| `audio_quality` | 2 |
| `pioneer_word` | 25 |
| `milestone_bonus` | 50 |

### Streak multipliers

| Streak | Multiplier |
|--------|------------|
| 100+ days | 5× |
| 30+ days | 3× |
| 7+ days | 2× |

`final_points = floor(base_points × max(streak_multiplier, event_multiplier))`

### Badge triggers

9 badges, defined in `init-db.sql` seed data, checked by `services/badges.py`:

| Badge | Condition |
|-------|-----------|
| Bronze Teacher | 100 total points |
| Silver Teacher | 1,000 total points |
| Gold Teacher | 10,000 total points |
| Legend Teacher | 100,000 total points |
| Correction Master | 50 words taught |
| Streak 7 | 7-day streak |
| Streak 30 | 30-day streak |
| Streak 100 | 100-day streak |
| Pioneer | 1 session completed |

Badges are checked after every session close via `_close_session()` in `routes/sessions.py`.

### Leaderboard cache

`GET /api/leaderboard?period=weekly` returns from Valkey (`leaderboard:weekly`, 5-min TTL). Cache is busted by `invalidate_leaderboard_cache()` after every session ends. Summary rebuild runs every 5 minutes as a background `asyncio.Task`.

---

## 12. Current Build Status (Phase Tracker)

| Phase | Status | What was built |
|-------|--------|----------------|
| Phase 0 — Infrastructure | ✅ Complete | docker-compose, Caddy, init-db.sql, .env.example, ML service |
| Phase 1 — Core Conversation | ✅ Complete | WS handler, prompt_builder, STT/LLM/TTS services, JWT auth, message persistence, learning cycle |
| Phase 2 — Frontend | ✅ Complete | Auth, onboarding, Orb, teach, home, ranks, settings, nav |
| Phase 3 — Gamification | ✅ Complete | Points, badges, leaderboard, summary rebuild, ORM models |
| Roadmap Weeks 7–10 | 🔲 Next | Speaker embeddings, async learning queue, GDPR consent, moderation |
| Roadmap Weeks 11–14 | 🔲 Future | VITS training, Whisper LoRA, LLM benchmarking, pipeline/ scripts |

### What still needs to be done before first real user test

**Critical path (blocking real user testing):**

1. **STT/TTS/LLM service availability** — The ML service (faster-whisper + mms-tts) and vLLM must be running. For local dev without GPU, set `GROQ_API_KEY` in `.env` to use Groq fallback. Current state: vLLM and ML services require GPU; fallback available but has latency.

2. **Speaker embedding extraction** — extract `vector(512)` embedding from each audio utterance using multilingual-e5-large and write to `speaker_embeddings`. Required for dialect clustering (roadmap Weeks 7–8). Currently: `speaker_embeddings` table exists but extraction pipeline not implemented.

3. **Async learning queue** — ✅ Implemented with Valkey-backed pending/processing/dead-letter queues and retry logic in the backend lifespan worker. Remaining gap: add monitoring/alerting for dead-letter growth.

**Quality (before shipping):**

4. **Alembic migrations** — `init-db.sql` handles first-run, but schema changes need numbered Alembic migration files in `backend/db/migrations/`.

5. **Moderation filter** — LIPI should reject corrections that appear to be spam or abuse. Currently no validation on correction_accepted events.

6. **GDPR consent workflow** — Users have `consent_audio_training` field but no UI to change it. Add a settings page section to toggle training data consent.

7. **CI/CD pipeline** — no automated tests or build pipeline yet. Tests should verify:
   - All endpoints return appropriate status codes
   - Education level values don't violate DB constraints
   - Tone profile cache has correct fields
   - JWT auth works for both Bearer and query-param modes

### Recently completed (was pending)

- ✅ **ORM ↔ DB alignment** — All 5 ORM models (User, TeachingSession, PointsTransaction, TeacherPointsSummary, TeacherBadge, Message) fixed to match actual PostgreSQL schema. Column names, UUID types (`postgresql.UUID(as_uuid=False)`), JSONB columns, NOT NULL defaults all corrected. All write paths verified.
- ✅ **Auth DB upsert** — `POST /api/auth/google` now creates or updates a `users` row from Google userinfo. JWT `sub` is the internal LIPI UUID (not Google sub). Response includes `user_id` and `onboarding_complete` flag.
- ✅ **Onboarding JWT-wired** — `POST /api/teachers/onboarding` uses `get_current_user` dep. The old dev `POST /api/teachers/onboarding/{user_id}` (path param, no auth) has been removed.
- ✅ **Volume mount** — `docker-compose.dev.yml` mounts `./backend:/app` so uvicorn `--reload` picks up changes without rebuilding the image.

### Latest fixes (2026-04-14)

**Problem:** Teach screen stuck on "Connecting..." after onboarding completion.

**Root causes & fixes:**

1. **Onboarding 500 — education_level constraint violation**
   - **Issue:** Frontend submitted display labels (e.g., `"Bachelor's"`) but database constraint requires canonical values (`"bachelors"`, `"masters"`).
   - **Fix:** `frontend/app/onboarding/page.tsx` — added `db` field to `EDUCATION_LEVELS` array with correct mapping. `finish()` function now looks up the database value before submitting: `const eduDbValue = eduLevel?.db || draft.education_level`.
   - **Status:** ✅ Verified with test submission.

2. **Session creation 500 — tone profile field mismatch**
   - **Issue:** `complete_onboarding()` in `backend/routes/teachers.py` cached tone profile with `first_name`/`last_name` keys, but `TeacherProfile` dataclass expects `name: str`.
   - **When `_load_tone_profile()` tried to instantiate:** `TeacherProfile(**cached_data)` raised `TypeError: missing required argument 'name'`.
   - **Fix:** `backend/routes/teachers.py:93-96` — changed tone profile cache to use `name: f"{first_name} {last_name}"` instead of separate fields.
   - **Backward compatibility:** `backend/routes/sessions.py:71-79` — added code to auto-migrate old cache entries: if cache has `first_name`/`last_name`, combines them into `name` before creating `TeacherProfile`.
   - **Status:** ✅ Demo user's stale Valkey cache auto-migrates; new onboarding saves correct format.

3. **Session endpoint unreachable from browser (CORS)**
   - **Issue:** Browser POST to `/api/sessions` from localhost:3000 was blocked by CORS when calling localhost:8000 directly.
   - **Fix:** `frontend/app/api/sessions/route.ts` — created Next.js API route that proxies POST to backend. Browser calls same-origin `/api/sessions?token=...`, route forwards to `http://localhost:8000/api/sessions?token=...`. No CORS conflict.
   - **Added logging:** Route now logs `[sessions proxy]` messages to help debug future connection issues.
   - **Status:** ✅ Proxy tested end-to-end; session creation succeeds with valid JWT.

**Verification:**
```bash
# Test demo login → session creation
docker exec lipi-backend bash -c 'TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/demo -H "Content-Type: application/json" | python3 -c "import sys,json; print(json.load(sys.stdin).get(\"access_token\",\"\"))") && curl -s -X POST "http://localhost:8000/api/sessions?token=$TOKEN" -H "Content-Type: application/json"'

# Response:
# {"session_id":"7f04c704...","user_id":"d0000000...","started_at":"2026-04-14T15:43:34.703104+00:00"}
```

**Full flow now works:**
1. Demo login → valid JWT
2. Onboarding completes → tone profile cached with `name` field
3. POST `/api/sessions` (proxied) → session created, returns session_id
4. WebSocket connects to `/ws/session/{id}?token=...` → conversation begins

---

## 13. Adding a New Feature (Checklist)

Before writing a line:
- [ ] Does this serve data collection or teacher retention? If not, don't build it.
- [ ] Is the feature in CLAUDE.md's build order? If not, ask before adding it.
- [ ] Does the backend service need a new ORM model? Add it to `models/` and verify every column name against `init-db.sql` — use `UUID(as_uuid=False)` for UUID columns, `JSONB` for jsonb columns. Mismatches cause silent 500s at runtime.
- [ ] Does the frontend need a new color? Add it as a CSS variable in all 4 theme blocks in `globals.css`.
- [ ] Does the frontend string have both Nepali and English? (Required.)

After writing:
- [ ] `/health` endpoint still returns `ok`
- [ ] No `from redis import` anywhere
- [ ] No hardcoded hex colors in TSX
- [ ] No static system prompt strings
- [ ] New API endpoint has a timeout on all external calls

---

## 14. Common Debugging

### "STT service not ready" on POST /stt

The ML container is still loading faster-whisper (large-v3 takes ~90s on first load from disk). Check: `docker compose logs ml --tail=20`. Wait for `"STT loaded"` and `"TTS loaded"`.

### vLLM returns 503

Either still loading (Qwen3-32B takes ~5 min cold) or ran OOM. Check: `docker compose logs vllm | grep -E "error|Error|OOM"`. If OOM: lower `--gpu-memory-utilization 0.85 → 0.75` in `docker-compose.yml`.

### Valkey connection refused

`valkey` container not started or URL wrong. Check `VALKEY_URL=valkey://valkey:6379/0` in `.env`. Inside Docker the hostname is `valkey`; outside Docker it's `localhost:6379`.

### Frontend shows blank/white flash on theme switch

The `ThemeProvider` sets `data-theme` in a `useEffect` (client-side). Add `suppressHydrationWarning` to `<html>` (already present in `layout.tsx`) and set a default `[data-theme="dark"]` CSS block so there's no flash before JS runs.

### WebSocket closes immediately (code 1011)

Check `docker compose logs backend`. Usually a Python exception during the first audio frame. Common causes: `ml` service not ready, audio frame arrives before VAD captures speech, or `user_id` lookup failing.

---

## 15. Glossary

| Term | Meaning |
|------|---------|
| Register | Nepali formality level: हजुर / तपाईं / तिमी / तँ |
| Tone profile | Per-teacher settings: register, energy, humor, code-switch ratio, phase |
| Phase (1/2/3) | Conversation depth: basics → daily life → stories |
| VAD | Voice Activity Detection — built into faster-whisper, no hold-to-talk |
| Pioneer word | First teacher to teach LIPI a word — earns 25 pts bonus |
| Correction card | Text overlay that slides up when LIPI detects a correction, fades after 3s |
| Summary rebuild | Background task that recalculates `teacher_points_summary` from raw log every 5 min |
| Valkey | BSD-3-licensed Redis fork. The one we use. Never "Redis". |
