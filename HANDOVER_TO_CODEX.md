# LIPI Handover to Codex — April 15, 2026

This is the canonical engineer handover file. If the state changes, update this file instead of creating another one-off handover/status summary.

## Current Status

**Architecture:** ✅ Stable hybrid local/remote stack  
**Backend:** ✅ Healthy, with multi-engine turn pipeline live  
**Database / Cache:** ✅ PostgreSQL + Valkey healthy  
**Frontend:** ✅ Auth, onboarding, session creation, WebSocket flow working  
**Remote Models:** ✅ Gemma + Whisper + Piper healthy on the remote host  
**Voice UX:** ⚠️ Working, but still not product-good  
**Data Quality:** ⚠️ Structured and improving, but still noisy

---

## What LIPI Is Right Now

LIPI is no longer blocked on infrastructure. The stack works.

The main problem has shifted from "can it run?" to:

- does it understand the teacher well enough
- does it ask good questions
- does it sound natural enough to keep people engaged
- is the resulting data clean enough to use later

The biggest remaining weaknesses are now:

1. **STT quality**, especially for Newari and mixed turns
2. **student behavior quality**, especially rigidity and over-confirming
3. **voice quality**, especially English delivery and overall tone

---

## What Works

1. **Core user flow**
   - Demo login works
   - Google login path is stable again with canonical auth origin
   - Onboarding works
   - Home / Teach / Ranks / Settings load
   - Session creation works
   - WebSocket conversation works
   - Live subtitles are visible on Teach

2. **Backend**
   - `GET /health` is green
   - hearing / interpretation / curriculum / personality / learning layers are live
   - durable Valkey learning queue is live
   - dashboard API is live at `/api/dashboard/overview`

3. **Remote inference**
   - LLM is **Gemma 4** behind a custom OpenAI-compatible shim on `:8100`
   - STT is **faster-whisper large-v3**
   - TTS is **Piper**
   - remote ML health is green

4. **Product instrumentation**
   - curriculum prompt events are logged
   - quality gate blocks weak turns from learning
   - topic memory is stored in Valkey
   - dashboard exposes data quality / coverage summaries
   - teacher turns now store raw / derived / gold training-data envelopes
   - teacher signal history is logged for behavior adaptation
   - async speaker-embedding capture now writes `vector(512)` rows into `speaker_embeddings`

---

## Current Architecture

### Local
- `frontend` on `http://127.0.0.1:3000`
- `backend` on `http://127.0.0.1:8000`
- `postgres`, `valkey`, `minio` in Docker

### Remote
- SSH target: `ekduiteen@202.51.2.50:41447`
- remote path: `/data/lipi`
- host-level Gemma server on `127.0.0.1:8100`
- remote ML container on `127.0.0.1:5001`
- remote Docker `backend`, `postgres`, `valkey`, `minio`

### Important runtime note
- the **actual live remote compose file** is:
  - `/data/lipi/docker-compose.lipi.yml`
- not the plain `docker-compose.yml`
- if a remote rebuild behaves strangely, check which compose file is actually being used before assuming source drift

---

## What Changed Recently

### Brain architecture
The backend now runs a more explicit multi-engine loop:

- `hearing.py`
- `turn_interpreter.py`
- `input_understanding.py`
- `teacher_modeling.py`
- `memory_service.py`
- `correction_graph.py`
- `behavior_policy.py`
- `response_orchestrator.py`
- `post_generation_guard.py`
- `training_capture.py`
- `audio_storage.py`
- `speaker_embeddings.py`
- `routing_hooks.py`
- `curriculum.py`
- `diversity.py`
- `personality.py`
- `response_cleanup.py`

This means the turn path is no longer just STT → prompt → LLM.

### Speaker embeddings
- ML service now exposes `/speaker-embed`
- async learning worker fetches saved teacher audio from MinIO
- backend validates 512-d vectors and writes them into `speaker_embeddings`
- current embedding implementation is `acoustic_signature_v1`
- new embeddings are assigned a lightweight incremental `dialect_cluster_id`
- dashboard now exposes speaker-embedding totals and cluster summary
- this is good enough for storage and early clustering, but it is not yet a learned speaker/dialect model

### Product behavior
- low-confidence STT turns now get clarification instead of bluffing
- multilingual turn guidance is live
- session topic memory is live
- curriculum prompt events and lane logic are live
- structured training-data capture is live on teacher turns
- teacher signal logging is live
- Newar-primary teacher targeting is live
- anti-parroting behavior improved for “you choose what to learn” moments

### Voice stack
- OmniVoice was removed from the live path
- current live TTS is Piper
- local code now supports **split TTS routing by language**
  - Nepali / Newari-leaning output → `ne_NP-google-medium`
  - English output → `en_US-lessac-medium`
- changed files: `ml/tts.py`, `backend/services/tts.py`, `ml/main.py`, `.env.example`
- **this split routing is coded locally but not fully confirmed live remotely**
  because the remote rebuild was interrupted during deployment

---

## What Is Still Weak

### 1. LIPI still feels too rigid
- too much confirmation
- too much constructed phrasing
- still sometimes says “I want to learn…” instead of asking directly

### 2. Voice quality is still not good enough
- Nepali Piper is acceptable as a baseline, not a polished brand voice
- English through the old single-voice path sounded wrong
- split language routing should help, but must still be deployed and tuned remotely

### 3. STT is still the main blocker for Newari quality
- Newari often collapses into `ne`
- mixed turns are still noisy
- bad hearing still contaminates higher-level behavior

### 4. Data is usable only with filtering
- structure is good
- latest turns are better than before
- still too noisy for blind fine-tuning

---

## Most Important Current Fixes

### Auth / session / browser issues
- canonical OAuth redirect origin
- onboarding proxy auth via cookie → Bearer forwarding
- session creation accepts Bearer or token query fallback
- WebSocket `about:blank` placeholder crash removed

### Data / behavior
- learner-meta cleanup tightened
- Newar-primary teachers now bias the conversation toward Newari
- invite-LIPI-choice intent added
- backend direct-choice path added so LIPI can ask a concrete question instead of only echoing

### Still unfinished
- direct-choice replies still need one more tuning pass to be less rigid
- split TTS routing needs full remote deployment confirmation

---

## Current Priorities

1. **Finish remote split-TTS deploy**
   - keep Nepali voice as `ne_NP-google-medium`
   - use separate English voice path

2. **Improve direct-question behavior**
   - less “I want to learn”
   - more immediate concrete questions

3. **Improve STT quality for Newari and mixed turns**
   - likely the single biggest lever for better data

4. **Reduce rigid confirmation**
   - especially in English
   - especially after the user invites LIPI to choose a topic

---

## Important Files

### Backend
- `backend/routes/sessions.py` — core conversation loop
- `backend/services/hearing.py` — transcript quality gate
- `backend/services/turn_interpreter.py` — turn meaning / intent inference
- `backend/services/personality.py` — response planning
- `backend/services/response_cleanup.py` — short spoken output enforcement
- `backend/services/prompt_builder.py` — system prompt + per-turn guidance
- `backend/services/curriculum.py` — question planning
- `backend/services/learning.py` — durable queue + learning gate
- `backend/routes/dashboard.py` — system/data dashboard API

### Frontend
- `frontend/app/(tabs)/teach/page.tsx` — Teach experience, subtitles, mic flow
- `frontend/lib/websocket.ts` — WebSocket client
- `frontend/app/api/proxy/[...path]/route.ts` — same-origin auth proxy
- `frontend/app/auth/page.tsx` — canonical auth origin logic

### ML
- `ml/main.py` — ML service app
- `ml/stt.py` — faster-whisper transcription logic
- `ml/tts.py` — Piper voice routing
- `backend/services/tts.py` — language-aware TTS routing client

### Infra / docs
- `scripts/gemma_openai_server.py` — Gemma OpenAI-compatible server
- `DEV_ONBOARDING.md` — living architecture guide
- `CLAUDE.md` — product / engineering source of truth

---

## Health Snapshot

At handover time, last known healthy state:

```json
backend: {"status":"ok","database":true,"valkey":true,"vllm":true,"ml_service":true}
ml: {"status":"ok","stt_loaded":true,"tts_loaded":true}
gemma: {"status":"ok","model":"gemma-4-E4B-it","device":"cuda"}
```

---

## Honest Assessment

LIPI now has a real backend brain.

The remaining problems are not “missing architecture” problems. They are mostly:

- hearing quality
- response feel
- voice quality
- multilingual data cleanliness

The next engineer should think less like “add another service” and more like:

**make LIPI feel like a believable multilingual student whose voice and questions are worth coming back to.**

---

## One-Line Truth

> The backend intelligence is now much stronger, but the product still feels weak mainly because of speech quality, rigid delivery, and STT limits — not because the core architecture is missing.
