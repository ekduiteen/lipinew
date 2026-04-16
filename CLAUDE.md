# LIPI — Engineering Master Brief
## Read this before writing a single line of code

You are the lead engineer on LIPI — a community-powered language data collection platform.
Every decision you make must serve the product vision, the architecture, and the constraints below.
Do not deviate. Do not gold-plate. Do not add features not listed here.

---

## What LIPI Is (Non-negotiable)

LIPI is **not** a language learning app. LIPI is **not** a chatbot.

LIPI is a **community data collection platform** disguised as a conversation.
- Users are **teachers**. LIPI is the **student**.
- Every conversation is **data collection** — audio, text, corrections, dialect signals.
- The student-teacher UX dynamic is the **data collection strategy**.
- Monthly LoRA fine-tuning on collected data is the **product flywheel**.

If a feature doesn't serve data collection or teacher retention, it doesn't get built.

---

## Hardware (What You Are Building For)

```
Server:    Own bare-metal (not cloud rental)
GPUs:      2× NVIDIA L40S (48GB VRAM each = 96GB total) — STARTING configuration
OS:        Ubuntu 22.04 + CUDA 12.1
RAM:       256GB
Storage:   4TB NVMe
Network:   1 Gbps uplink
```

**GPU allocation (current tested: single L40S):**
```
GPU 0:  vLLM serving Qwen2.5-14B-Instruct-AWQ (AWQ quantized, fits single L40S)
        + faster-whisper large-v3 STT (~3GB, shares GPU 0)
        + OmniVoice TTS (~2GB, shares GPU 0)
```

> **Future:** Cluster configuration with 2× L40S supports tensor-parallel larger models. Current production uses AWQ quantization for single-GPU efficiency.

**vLLM launch command:**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-14B-Instruct-AWQ \
  --dtype auto \
  --gpu-memory-utilization 0.85 \
  --port 8100 \
  --enable-prefix-caching \
  --max-model-len 8192 \
  --served-model-name lipi
```

---

## Complete Tech Stack (Locked — Do Not Substitute)

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 14 (App Router) + TypeScript | PWA-first, web before mobile |
| Mobile (Phase 2) | Flutter | iOS + Android from one codebase |
| Backend | FastAPI (Python 3.11) | Async, fast, GPU-friendly ecosystem |
| LLM inference | vLLM (OpenAI-compatible API) | Best throughput for self-hosted |
| LLM model | Gemma 4 (current live) | Running on remote host behind OpenAI-compatible shim on `:8100` |
| LLM model | Qwen2.5-14B-Instruct-AWQ | Target spec (201 languages, fits single L40S); not yet deployed |
| STT | faster-whisper large-v3 | 99 languages, VAD built-in, dialect LoRA support |
| TTS | Piper | Current live (language-aware routing: Nepali `ne_NP-google-medium`, English separate) |
| TTS (planned) | OmniVoice | Was Phase 1, deprioritized in favor of Piper |
| Database | PostgreSQL 16 + pgvector | Structured data + speaker embeddings |
| Cache / Queues | **Valkey** (NOT Redis — Redis is SSPL) | BSD-3 licensed Redis fork |
| Object storage | MinIO | S3-compatible, self-hosted, AGPL |
| Reverse proxy | **Caddy** (NOT nginx) | Auto HTTPS, simpler config, self-hosted |
| Deployment | Coolify | Self-hosted Vercel alternative |
| Monitoring | Prometheus + Grafana | Standard OSS observability |
| API fallback | Groq (Whisper STT + LLaMA LLM) | Reliability fallback ONLY — not primary |

**Zero paid SaaS in the critical path. API fallback fires only when local inference fails.**

---

## Project Structure (Updated 2026-04-17)

```
lipi/
├── CLAUDE.md                    ← you are here
├── DEV_ONBOARDING.md            ← living architecture guide (more detailed)
├── HANDOVER_TO_CODEX.md         ← handover notes + known issues
├── docker-compose.yml
├── Caddyfile
├── .env.example
│
├── frontend/                    # Next.js 14 PWA (App Router)
│   ├── app/
│   │   ├── auth/page.tsx        # Google OAuth sign-in
│   │   ├── onboarding/page.tsx  # 7-question bilingual onboarding
│   │   ├── (tabs)/              # 6-tab navigation layout
│   │   │   ├── home/page.tsx           # Dashboard + stats
│   │   │   ├── teach/page.tsx          # Orb + WebSocket conversation
│   │   │   ├── phrase-lab/page.tsx     # Structured phrase capture (NEW)
│   │   │   ├── heritage/page.tsx       # Heritage/dialect capture (NEW)
│   │   │   ├── ranks/page.tsx          # Leaderboard
│   │   │   └── settings/
│   │   │       ├── page.tsx            # Theme picker + dashboard link
│   │   │       └── dashboard/page.tsx  # System health API
│   │   └── api/                 # Next.js API routes (proxy + auth)
│   ├── components/
│   │   ├── orb/Orb.tsx          # 4-state animated orb
│   │   ├── theme/ThemeProvider.tsx
│   │   ├── ui/BottomNav.tsx     # 6-tab nav (was 4)
│   │   └── phrase-lab/          # Phrase Lab components (NEW)
│   └── lib/
│       ├── websocket.ts         # WebSocket client
│       └── api.ts               # REST client
│
├── backend/                     # FastAPI (Python 3.11)
│   ├── main.py                  # App factory, route registration
│   ├── config.py                # pydantic-settings
│   ├── cache.py                 # Valkey client
│   ├── jwt_utils.py
│   ├── rate_limit.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── sessions.py          # Core WS conversation + session mgmt
│   │   ├── teachers.py
│   │   ├── leaderboard.py
│   │   ├── dashboard.py         # System health + data overview
│   │   ├── phrases.py           # Phrase Lab REST API (NEW)
│   │   └── heritage.py          # Heritage REST API (NEW)
│   ├── services/                # ~30 service modules covering all logic
│   │   ├── llm.py, stt.py, tts.py  # Model API clients
│   │   ├── prompt_builder.py
│   │   ├── points.py, badges.py, learning.py
│   │   ├── hearing.py, turn_interpreter.py, input_understanding.py
│   │   ├── teacher_modeling.py, memory_service.py
│   │   ├── behavior_policy.py, response_orchestrator.py, personality.py
│   │   ├── curriculum.py, diversity.py
│   │   ├── correction_graph.py, phrase_pipeline.py, speaker_embeddings.py
│   │   ├── heritage_prompt.py   # Heritage mode prompt generation (NEW)
│   │   └── [+17 more services detailed in DEV_ONBOARDING.md]
│   ├── models/                  # SQLAlchemy 2.0 ORM
│   │   ├── user.py, session.py, points.py, badge.py, message.py
│   │   ├── curriculum.py, intelligence.py, phrases.py
│   │   └── heritage.py          # HeritageSession ORM (NEW)
│   ├── db/
│   │   ├── connection.py
│   │   ├── init_db.py
│   │   └── [DO NOT EDIT: use Alembic migrations]
│   ├── alembic/                 # Schema version control (6 migrations)
│   │   └── versions/
│   │       ├── 91ba4c4fe766_initial_schema.py
│   │       ├── a7c6e1d9f210_phrase_lab_and_review_queue.py
│   │       ├── b8d7e4c3f920_heritage_sessions.py  (NEW)
│   │       └── [3 more intelligence + curriculum migrations]
│   ├── tests/                   # pytest suite (16 test files)
│   └── dependencies/
│       └── auth.py              # JWT helpers
│
├── ml/                          # GPU microservice (STT + TTS)
│   ├── main.py                  # FastAPI /health /stt /tts /speaker-embed
│   ├── stt.py                   # faster-whisper large-v3
│   ├── speaker_embed.py         # acoustic_signature_v1 (512-d)
│   ├── tts.py, tts_piper.py, tts_coqui.py, tts_provider.py
│   ├── requirements.txt
│   └── Dockerfile
│
└── pipeline/                    # Monthly LoRA fine-tuning (PHASE 4 — not yet built)
    ├── prepare_data.py          # TBD
    ├── train_lora.py            # TBD
    ├── eval.py                  # TBD
    └── announce.py              # TBD
```

---

## Architecture Decisions (Understand Before Coding)

### 1. WebSocket is the core transport
Every conversation runs over a single persistent WebSocket.
```
Client → WS /ws/session/{session_id}
  Audio chunks → STT → LLM → TTS → Audio response
  All within the same connection.
```
REST endpoints are for metadata only (create session, get stats, leaderboard).

### 2. System prompts are dynamic, not static
Every session gets a freshly assembled system prompt from:
- Teacher's name, age, register (tapai/timi/ta/hajur)
- Gender (determines address terms and verb forms)
- Energy level, humor level, code-switch ratio
- Session phase (1/2/3 → question bank)
- Previous topics, preferred topics

See `SYSTEM_PROMPTS.md` for full templates and assembly logic.

### 3. Valkey (not Redis) for all caching
```python
# Always import from valkey, never redis
from valkey.asyncio import Valkey
valkey = Valkey.from_url(os.getenv("VALKEY_URL"))
```

### 4. Points are an immutable event log
`points_transactions` is append-only. Never update, never delete.
`teacher_points_summary` is a cache rebuilt from transactions every 5 min.
See `GAMIFICATION_DATA_MODEL.md` for full schema.

### 5. API fallback is a circuit breaker, not a router
```python
async def generate_llm(messages: list) -> str:
    try:
        return await vllm_generate(messages, timeout=8.0)
    except Exception:
        log_fallback_event("llm")
        return await groq_generate(messages)  # fires only on local failure
```

### 6. Bilingual always — Nepali leads
Every user-facing string has Nepali and English.
Nepali is `primary`, English is `secondary`.
Store both in translation files, never hardcode.

### 7. No cultural imagery
Futuristic dark aesthetic. No flags, patterns, traditional colors in the default theme.
Traditional theme is opt-in (user selects in settings).

---

## Database Schema Reference

**Core gamification tables** (see `GAMIFICATION_DATA_MODEL.md`):
```
teacher_tone_profiles       — communication style per teacher
points_transactions         — immutable points event log
teacher_points_summary      — cached totals (5-min rebuild)
badges                      — badge definitions (9 types)
teacher_badges              — earned badges per teacher
leaderboard_snapshots       — weekly/monthly period snapshots
teaching_sessions           — session metadata
session_corrections         — correction events
session_prompt_snapshots    — audit log of prompts used
```

**Core language learning tables** (see `DATABASE_SCHEMA.md`):
```
users                       — teacher profiles
conversation_sessions       — (legacy name, same as teaching_sessions)
messages                    — per-turn message log
vocabulary_entries          — words LIPI has learned
grammar_entries             — grammar rules LIPI has learned
speaker_embeddings          — dialect clustering data
```

**Always use pgvector for embeddings:**
```sql
-- Speaker embedding storage
embedding vector(512)  -- multilingual-e5-large output dim
```

---

## UI/UX Constraints (See `UI_UX_DESIGN.md`)

### The conversation screen has NO text (except corrections)
```
✓ Orb animation only
✓ Text card slides up ONLY when LIPI registers a correction
✓ Text card fades after 3 seconds
✗ No chat bubbles
✗ No transcript display
✗ No hold-to-talk button (auto-detect VAD)
```

### 5 themes via CSS variables — "Pastel Intelligent Minimalism"
```css
/* Root always has data-theme attribute — set synchronously before first paint */
/* layout.tsx injects a blocking script that reads localStorage before CSS evaluates */
/* Orb reads --orb-a, --orb-b, --orb-c */
[data-theme="pastel"]   { --bg: #F8F6F2; --accent: #2E2E2E; --orb-a: #CBBBEF; ... }  /* DEFAULT */
[data-theme="warm"]     { --bg: #FAF7F2; --accent: #5C3A1E; --orb-a: #E8C4A0; ... }
[data-theme="lavender"] { --bg: #F4F0FA; --accent: #6B4FA0; --orb-a: #C8B4F0; ... }
[data-theme="sage"]     { --bg: #F0F5F0; --accent: #2A5A2A; --orb-a: #B8D8B8; ... }
[data-theme="dark"]     { --bg: #0F0F14; --accent: #8B7FD4; --orb-a: #6366f1; ... }
```

### Navigation — 6 tabs (expanded from original 4)
```
[Home]  [Teach]  [Heritage]  [Phrase Lab]  [Ranks]  [Settings]
```

**Update:** Product now has two structured data-collection lanes:
- **Teach**: Open-ended conversation (original core)
- **Heritage**: Dialect/register capture via guided prompts (NEW)
- **Phrase Lab**: Structured phrase + variation recording (NEW)

All remain data-collection first, with teacher retention as the north star.

### Onboarding — 7 questions, bilingual
```
Nepali text (large, primary) on top
English text (small, secondary) below
One question per screen, thin progress bar, no numbers
```

---

## Points System (See `GAMIFICATION_DATA_MODEL.md`)

```python
POINT_VALUES = {
    "session_base":         10,
    "word_learned":          5,
    "correction_accepted":  15,   # corrections worth most
    "audio_quality":         2,
    "pioneer_word":         25,
    "milestone_bonus":      50,
}
MULTIPLIERS = {
    "streak_7_days":    2.0,
    "streak_30_days":   3.0,
    "streak_100_days":  5.0,
    "rare_dialect":     3.0,
    "minority_language": 2.0,
}
```

---

## Performance Targets

| Metric | Target |
|--------|--------|
| STT latency | < 200ms |
| LLM first token | < 2s |
| TTS generation | < 500ms |
| End-to-end (voice in → audio out) | < 3s |
| WebSocket connection | < 100ms |
| Leaderboard API | < 50ms (Valkey cached) |
| Page load (Next.js) | < 1.5s FCP |

---

## Environment Variables

```bash
# LLM
VLLM_URL=http://vllm:8080
VLLM_MODEL=lipi
GROQ_API_KEY=...           # fallback only

# ML Service
ML_SERVICE_URL=http://ml:5001

# Database
DATABASE_URL=postgresql+asyncpg://lipi:password@postgres:5432/lipi

# Valkey (NOT Redis)
VALKEY_URL=valkey://valkey:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET_AUDIO=lipi-audio
MINIO_BUCKET_TTS=lipi-tts

# Auth
NEXTAUTH_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# App
APP_URL=https://lipi.app
ENVIRONMENT=production
```

---

## What Has Been Designed (Do Not Redesign)

All design decisions are final. Read these docs before touching the related code:

| Doc | Covers |
|-----|--------|
| `LIPI_PHILOSOPHY.md` | Why LIPI exists, student-teacher dynamic |
| `SYSTEM_PROMPTS.md` | All prompt templates, registers, assembly logic |
| `UI_UX_DESIGN.md` | All screens, brand, themes, bilingual rules |
| `GAMIFICATION_DATA_MODEL.md` | Points, badges, leaderboards, tone profiles |
| `DATABASE_SCHEMA.md` | Core language learning tables |
| `STT_ARCHITECTURE.md` | faster-whisper setup, dialect LoRA |
| `TTS_ARCHITECTURE.md` | OmniVoice setup, Phase 2 training |
| `STUDENT_CHARACTER_DESIGN.md` | LIPI's personality, moderation, questions |
| `DEPLOYMENT.md` | Docker Compose, Caddy, Coolify |

---

## Build Order (Phase 0 → MVP)

### Phase 0 — Infrastructure (Week 1-2)
```
1. docker-compose.yml (all services)
2. Caddyfile (reverse proxy + auto HTTPS)
3. init-db.sql (PostgreSQL schema + pgvector)
4. ML service skeleton (STT + TTS FastAPI)
5. vLLM server running Qwen2.5-14B-Instruct-AWQ
6. Health checks on all services
```

### Phase 1 — Core Conversation (Week 3-6)
```
7.  FastAPI WebSocket handler (/ws/session/{id})
8.  prompt_builder.py (dynamic system prompt assembly)
9.  STT pipeline (audio → faster-whisper → text)
10. LLM pipeline (text → vLLM → text) + fallback
11. TTS pipeline (text → OmniVoice → audio) + fallback
12. Session creation + tear-down
13. Points transaction logging
```

### Phase 2 — Frontend (Week 5-8, parallel with Phase 1)
```
14. Next.js project setup + theme system
15. Auth screen (Google + phone)
16. Onboarding flow (7 questions)
17. Orb animation component (4 states, CSS/Canvas/Lottie)
18. Conversation screen (WebSocket client, VAD)
19. Correction text overlay (slides up, fades)
20. Home screen (stats, mini leaderboard, CTA)
21. Ranks screen (leaderboard tabs)
22. Settings screen (theme picker with live previews)
```

### Phase 3 — Gamification (Week 7-10)
```
23. Badge award system
24. Leaderboard API + Valkey cache
25. Points summary rebuild (cron)
26. Weekly/monthly snapshot jobs
27. Session summary card
28. Community feed
```

---

## Coding Standards

### Python (FastAPI, ML service)
- Python 3.11+, async everywhere
- SQLAlchemy 2.0 async ORM (not raw SQL except for complex queries)
- Pydantic v2 for all request/response schemas
- httpx for all HTTP calls (not requests)
- tenacity for retry logic on fallbacks
- Never use `from redis import ...` — always `from valkey import ...`

### TypeScript (Next.js)
- Strict mode on
- App Router only (not Pages Router)
- Server Components by default, Client Components only when needed
- CSS variables for all theme values — no hardcoded colors
- Web Audio API for microphone (not MediaRecorder directly)

### SQL
- Migrations only via numbered files in `db/migrations/`
- Never ALTER TABLE in application code
- pgvector for all embedding storage
- Always use parameterized queries

### General
- No `print()` in production code — use `logging`
- Every service has a `/health` endpoint
- Every external call has a timeout
- No secrets in code — only `os.getenv()`
- Docker Compose for local dev, Coolify for production

---

## Forbidden Patterns

```python
# NEVER — Redis is SSPL licensed
from redis import Redis

# NEVER — hardcoded secrets
VLLM_URL = "http://localhost:8080"

# NEVER — blocking calls in async handlers
result = requests.post(...)  # use httpx instead

# NEVER — static system prompts
SYSTEM_PROMPT = "You are LIPI..."  # use prompt_builder.py

# NEVER — storing points without validation
INSERT INTO points_transactions (validated=True) ...
# validation must pass first
```

---

## The North Star

Every line of code serves one goal:
**Make teachers feel like their voice matters enough to come back tomorrow.**

If it doesn't do that, it doesn't ship.
