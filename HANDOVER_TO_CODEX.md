# LIPI Handover — April 17, 2026

This is the canonical engineer handover file. Update this file when state changes — do not create separate one-off status files.

## Current Status — STABLE v2 ✅

| Layer | Status | Notes |
|-------|--------|-------|
| Backend | ✅ Healthy | All routes stable, WebSocket pipeline clean |
| Database | ✅ Healthy | PostgreSQL + pgvector, 6 Alembic migrations |
| Cache | ✅ Healthy | Valkey (Redis fork) |
| Object Storage | ✅ Healthy | MinIO |
| Frontend | ✅ Rebuilt | Full design system, dark mode working |
| Remote LLM | ✅ Live | Gemma 4 via vLLM on `:8100` |
| Remote STT | ✅ Live | faster-whisper large-v3 on `:5001` |
| Remote TTS | ✅ Live | Piper on `:5001` |
| Phrase Lab | ✅ Working | Recording → WAV → STT → DB pipeline working |
| Heritage | ✅ Working | Same pipeline, fixed auth + audio format |
| Dark mode | ✅ Fixed | No flash on load, theme persists correctly |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│           LOCAL (Docker Compose)             │
├─────────────────────────────────────────────┤
│ Frontend (Next.js 14 PWA)      :3000 ✅     │
│ Backend (FastAPI Python 3.11)  :8000 ✅     │
│ PostgreSQL 16 + pgvector       :5432 ✅     │
│ Valkey (Redis BSD fork)        :6379 ✅     │
│ MinIO (S3-compatible)          :9000 ✅     │
└─────────────────────────────────────────────┘
            ↕ SSH Tunnel (port 41447)
┌─────────────────────────────────────────────┐
│      REMOTE (202.51.2.50)                   │
├─────────────────────────────────────────────┤
│ vLLM (Gemma 4 E4B-it)          :8100 ✅     │
│ ML Service (STT/TTS/embed)     :5001 ✅     │
│  ├─ faster-whisper large-v3                 │
│  ├─ Piper TTS (ne + en voices)             │
│  └─ Speaker embeddings (512-d)             │
└─────────────────────────────────────────────┘
```

**Remote compose file:** `/data/lipi/docker-compose.lipi.yml` (not the plain `docker-compose.yml`)

### SSH Tunnel
```bash
ssh -N -p 41447 \
  -L 8100:localhost:8100 \
  -L 5001:localhost:5001 \
  ekduiteen@202.51.2.50
```

---

## What Changed in v2 (April 17)

### 1. Design System — "Pastel Intelligent Minimalism"
Complete frontend redesign. All screens now use a unified design system.

**Themes (5, selectable in Settings):**
- `pastel` — Pastel Light (default)
- `warm` — Warm Cream
- `lavender` — Lavender Mist
- `sage` — Sage Air
- `dark` — Dark

**Token system in `globals.css`:**
- Color: `--bg`, `--bg-card`, `--bg-elev`, `--bg-frost`, `--fg`, `--fg-muted`, `--fg-subtle`, `--accent`, `--border`
- Pastel accents: `--pastel-lavender`, `--pastel-sage`, `--pastel-peach`, `--pastel-sky`, `--pastel-butter`
- Spacing: `--space-1` through `--space-12`
- Shape: `--radius-sm/md/lg/xl/full`
- Component classes: `.card`, `.card-frost`, `.btn-primary`, `.btn-secondary`, `.btn-text`, `.btn-mic`, `.bilingual`, `.stat-card`, `.chip`, `.spinner`, `.page`, `.fade-in`

**Screens updated:**
- `app/page.tsx` — Splash
- `app/auth/page.tsx` + `auth.module.css` — Sign in
- `app/onboarding/onboarding.module.css` — Replaced cyberpunk hardcodes with CSS tokens
- `app/(tabs)/home/page.tsx` — Dashboard (migrated from module.css)
- `app/(tabs)/teach/page.tsx` — Uses global btn classes
- `app/(tabs)/phrase-lab/page.tsx` — Full design system
- `app/(tabs)/heritage/page.tsx` — Full redesign
- `app/(tabs)/ranks/page.tsx` — Migrated from module.css
- `app/(tabs)/settings/page.tsx` — Theme names fixed

### 2. Dark Mode Flash Fix
**Problem:** Theme flashed light→dark on every page load because `ThemeProvider` set `data-theme` in a `useEffect` (after paint).

**Fix:**
- `layout.tsx` — Inline blocking script in `<head>` reads `localStorage` and sets `data-theme` on `<html>` before any CSS evaluates
- `ThemeProvider` — Initializes state from `document.documentElement.getAttribute('data-theme')` instead of hardcoded `"pastel"` — no `setState` flash

### 3. Phrase Lab & Heritage Audio Fix
**Problem:** `MediaRecorder` outputs `audio/webm`, but the ML service uses `soundfile.read()` which does not support WebM. Every recording submission returned 500 → "Connection error".

**Fix:** `blobToWav()` helper added to both pages:
1. `AudioContext.decodeAudioData()` decodes the WebM blob
2. Downmix to mono
3. Re-encode as 16-bit PCM WAV at 16kHz using `encodeWav()`
4. Send `phrase.wav` / `heritage.wav` to backend instead of `.webm`

The Teach page was unaffected because it already encoded WAV manually.

### 4. Heritage Auth Fix
Heritage page was reading `localStorage.getItem("lipi.token")` and sending it as `Authorization: Bearer ...`. Token is stored in an httpOnly cookie — localStorage is always empty.

**Fix:** Removed `getToken()`, switched to `credentials: "include"` on all fetch calls.

### 5. Settings Theme Names Fix
`settings/page.tsx` had `THEME_META` with keys `dark/bright/cyberpunk/traditional` — but `ThemeProvider` exported `pastel/warm/lavender/sage/dark`. Theme picker was broken.

**Fix:** Updated `THEME_META` to match the actual theme keys.

### 6. Auto Phrase Generation
`backend/services/phrase_generator.py` — Background asyncio task that:
- Runs every 5 minutes
- Checks if active phrase count < 20
- Calls Gemma 4 via vLLM to generate 3 phrases per category
- Inserts as `is_active=True`, `review_status="approved"`
- Started in `backend/main.py` lifespan

Current DB: 30 phrases across 6 categories (greetings, questions, statements, introductions, politeness, requests).

---

## Data Snapshot (April 17)

```
users:               4 (3 active)
phrases:            30 (all active, approved)
teaching_sessions:  88
messages:          302
points_transactions: 307
phrase_submissions:  0  ← nobody has submitted through phrase lab yet
teacher_badges:      0
```

**Points by type:**
- `pioneer_word` — 2,500 pts (100 events)
- `session_base` — 780 pts (78 sessions)
- `word_learned` — 500 pts (100 events)
- `correction_accepted` — 435 pts (29 events)

---

## What Works

### Core user flow
- Demo login + Google OAuth
- Onboarding (7 questions, bilingual)
- Home dashboard (stats + mini leaderboard)
- Teach tab: WebSocket conversation, VAD, subtitle overlay, correction cards
- Phrase Lab: hold-to-record → WAV upload → STT → quality check → DB
- Heritage: mode selection → hold-to-record → WAV upload → follow-up prompt
- Ranks: weekly/monthly/all-time leaderboard
- Settings: 5-theme picker with live orb preview, dashboard link
- Dark mode: flash-free, persists across navigation

### Backend
- `/health` — all green
- WebSocket turn pipeline: hearing → STT → LLM → TTS → audio response
- Phrase Lab REST API: next/skip/submit-audio/submit-variation-audio
- Heritage REST API: create session / submit primary / submit followup
- Auto phrase generation (background job, every 5 min)
- Points system (immutable event log)
- Speaker embeddings (512-d, async capture)

---

## What Is Still Weak

1. **STT for Newari** — Newari often collapses to `ne`; mixed turns noisy
2. **LLM response feel** — Sometimes too rigid/formal, especially in English
3. **Voice quality** — Piper is acceptable baseline, not premium
4. **Phrase submissions = 0** — The pipeline is proven (recording works), but no one has completed a full Phrase Lab session through to DB commit yet
5. **phrase_generation_batches = 0** — Phrases were seeded directly; the LLM background job hasn't fired yet (needs 5-min idle window after startup)
6. **Split TTS routing** — Coded locally (ne → `ne_NP-google-medium`, en → `en_US-lessac-medium`), not confirmed deployed on remote

---

## Current Priorities

1. **Confirm phrase_generation_batches start filling** — verify background job is firing
2. **First complete Phrase Lab session** — record → submit → see row in `phrase_submissions`
3. **STT quality for Newari** — biggest data quality lever
4. **Split TTS deploy confirmation** — check remote ML service config

---

## Important Files

### Frontend
| File | Purpose |
|------|---------|
| `frontend/app/globals.css` | Design system — all tokens + component classes |
| `frontend/app/layout.tsx` | Root layout — theme flash prevention script |
| `frontend/components/theme/ThemeProvider.tsx` | Theme state + DOM sync |
| `frontend/components/ui/BottomNav.tsx` | 6-tab navigation |
| `frontend/components/orb/Orb.tsx` | 4-state animated orb |
| `frontend/app/(tabs)/teach/page.tsx` | WebSocket conversation + VAD |
| `frontend/app/(tabs)/phrase-lab/page.tsx` | Phrase Lab + blobToWav() |
| `frontend/app/(tabs)/heritage/page.tsx` | Heritage + blobToWav() |
| `frontend/lib/websocket.ts` | WebSocket client |

### Backend
| File | Purpose |
|------|---------|
| `backend/routes/sessions.py` | Core WebSocket conversation loop |
| `backend/routes/phrases.py` | Phrase Lab REST API |
| `backend/routes/heritage.py` | Heritage REST API |
| `backend/services/phrase_pipeline.py` | Phrase audio processing pipeline |
| `backend/services/phrase_generator.py` | Auto LLM phrase generation (background) |
| `backend/services/hearing.py` | Transcript quality gate |
| `backend/services/stt.py` | STT client (local + Groq fallback) |
| `backend/dependencies/auth.py` | JWT auth — reads httpOnly cookie |
| `backend/main.py` | App factory + lifespan (phrase gen task) |

### ML
| File | Purpose |
|------|---------|
| `ml/stt.py` | faster-whisper transcription (reads WAV/FLAC/OGG — NOT WebM) |
| `ml/tts.py` | Piper TTS with language routing |
| `ml/main.py` | ML service FastAPI app |

---

## Critical Notes for Next Engineer

### Audio Format
**The ML STT service uses `soundfile` — it cannot read WebM/Opus.**
Any page that records audio must convert to WAV before uploading.
Use the `blobToWav()` helper in phrase-lab or heritage page as reference.
The Teach page encodes WAV manually via `encodeWav()` in `teach/page.tsx`.

### Auth Pattern
Token is in an **httpOnly cookie** (`lipi.token`), not localStorage.
- Frontend: always use `credentials: "include"` on fetch calls
- Backend: `get_current_user()` in `dependencies/auth.py` reads from cookie first, then Authorization header
- Never read `localStorage.getItem("lipi.token")` — it will always be empty

### Valkey (not Redis)
```python
from valkey.asyncio import Valkey  # ALWAYS — never from redis import
```

### Database changes
Use Alembic. Never ALTER TABLE in application code. Current: 6 migrations.

---

## Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok","database":true,"valkey":true,"vllm":true,"ml_service":true}

curl http://localhost:5001/health
# {"status":"ok","stt_loaded":true,"tts_loaded":true,"speaker_embed_loaded":true}
```
