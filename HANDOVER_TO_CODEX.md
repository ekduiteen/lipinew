# LIPI Handover to Codex — April 15, 2026

## Current Status

**Architecture:** ✅ Stable hybrid local/remote  
**Backend:** ✅ Running in Docker, healthy  
**Database / Cache:** ✅ PostgreSQL + Valkey healthy  
**Frontend:** ✅ Loading, auth working, Teach usable  
**Remote Model Services:** ✅ Gemma LLM + ML service healthy through SSH tunnel  
**Voice Loop:** ⚠️ Working but still weak on English understanding and conversation quality  

---

## What Works

1. **Core app flow**
   - Demo login works
   - Onboarding works
   - Home / Teach / Ranks / Settings render
   - Session creation works
   - WebSocket conversation works
   - Live subtitles are visible on Teach

2. **Backend**
   - `GET /health` is green locally
   - DB schema is initialized
   - durable Valkey learning queue is live
   - dashboard API is live at `/api/dashboard/overview`

3. **Remote inference**
   - LLM is **Gemma 4** behind a custom OpenAI-compatible shim on `:8100`
   - STT is **faster-whisper large-v3**
   - TTS is **Piper** (`ne_NP-google-medium`)
   - remote ML health is green

4. **Frontend/backend connectivity**
   - browser auth requests no longer hang
   - REST requests go through same-origin Next proxy routes
   - Teach has explicit status text and a manual mic start flow

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

### Tunnel
- local `127.0.0.1:8000` → backend
- local `127.0.0.1:5001` → remote ML
- local `127.0.0.1:8100` → remote Gemma server

---

## What Changed Recently

### LLM / conversation behavior
- Qwen/vLLM path replaced with **Gemma 4** OpenAI-compatible shim
- Nepali purity guardrails added
- repeated weird endings and parenthetical self-commentary reduced
- hardcoded kinship guesses like `भाइ` removed
- multilingual turn guidance added so English / mixed / local-language turns can be handled differently
- lightweight topic memory added per session in Valkey

### STT / TTS
- TTS moved from OmniVoice to **Piper Nepali**
- remote Whisper updated to try a better Nepali/English candidate order
- STT and TTS are hot-loaded on the remote ML service

### Data / observability
- durable Valkey learning queue implemented
- quality gate added before learning enqueue
- dashboard added for:
  - health
  - queue depth
  - data quality
  - recent turns

---

## What Is Still Weak

### 1. English understanding is still not strong enough
- recent stored turns still show many teacher transcripts labeled `ne`
- English and mixed-language speech are still often mangled by STT
- remote Whisper logic was updated and redeployed, but real-world quality is still not where it needs to be

### 2. LIPI still feels like a weak student
- it still drifts into “teach me” / lesson-meta behavior too easily
- it does not take conversation forward strongly enough yet
- follow-up questions are better than before, but not consistently smart

### 3. Multilingual ambition is only partially implemented
- the prompt now has hooks for English / mixed / local-language turns
- topic memory now tracks active language and taught words
- but Newari / other-language support is not yet first-class in onboarding, extraction, or reporting

---

## Current Priorities

1. **Improve live STT quality**
   - especially English and mixed Nepali/English speech
   - if Whisper continues to fail, evaluate alternate STT strategy rather than prompt-tuning around bad transcripts

2. **Strengthen student behavior**
   - respond to meaning first
   - ask only one topic-relevant follow-up
   - avoid generic “teach me” loops

3. **Make multilingual learning explicit**
   - Newari / other-language teaching should become a first-class path, not a side effect

4. **Improve structured memory**
   - corrections
   - taught words by language
   - topic continuity

---

## Important Files

### Backend
- `backend/routes/sessions.py` — core conversation loop
- `backend/services/prompt_builder.py` — system prompt + per-turn guidance
- `backend/services/llm.py` — Gemma reply generation, cleanup, purity rules
- `backend/services/topic_memory.py` — lightweight session memory
- `backend/services/learning.py` — durable queue + vocabulary extraction
- `backend/routes/dashboard.py` — system/data dashboard API

### Frontend
- `frontend/app/(tabs)/teach/page.tsx` — Teach experience, subtitles, mic flow
- `frontend/lib/websocket.ts` — WebSocket client
- `frontend/lib/api.ts` — API calls
- `frontend/app/api/proxy/[...path]/route.ts` — same-origin proxy for REST

### ML
- `ml/main.py` — ML service app
- `ml/stt.py` — faster-whisper transcription logic
- `ml/tts.py` — Piper TTS

### Infrastructure
- `scripts/gemma_openai_server.py` — Gemma OpenAI-compatible server
- `DEV_ONBOARDING.md` — living architecture guide
- `CLAUDE.md` — product and engineering source of truth

---

## Health Snapshot

At handover time:

```json
backend: {"status":"ok","database":true,"valkey":true,"vllm":true,"ml_service":true}
ml: {"status":"ok","stt_loaded":true,"tts_loaded":true}
```

---

## Honest Assessment

LIPI is no longer blocked on infrastructure. The stack works.

The real problem now is **product quality**:
- STT still misunderstands too much
- LIPI is still too passive and lesson-shaped
- multilingual behavior is only partially realized

So the next engineer should think less like “make services boot” and more like:

**make LIPI feel like a curious multilingual student whose conversations are worth collecting as data.**
