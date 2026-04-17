# LIPI — Stable v1 Release
**Date:** 2026-04-16  
**Status:** ✅ **PRODUCTION-READY LOCAL STACK**

---

## What's Fixed in v1

### 1. Backend AttributeError Fixes
**Problem:** WebSocket connections were failing with code 1011 "internal error"

**Root Causes & Fixes:**
- ❌ `routing_hooks.py:32` — Referenced non-existent `understanding.dialect_hook`
  - ✅ Changed to `understanding.dialect_guess` (actual attribute on InputUnderstanding)
  
- ❌ `response_orchestrator.py:66` — Referenced non-existent `understanding.quality_label`
  - ✅ Removed. Added `understanding.emotion` instead for richer context
  
- ❌ `response_orchestrator.py:67` — Referenced non-existent `understanding.dialect_hook`
  - ✅ Removed (redundant with dialect_guess already on next line)

### 2. Docker Port Forwarding Fix
**Problem:** Frontend couldn't reach backend from browser on Windows Docker Desktop

**Fix:**
- Changed `docker-compose.yml` frontend environment:
  - `NEXT_PUBLIC_BACKEND_URL: http://127.0.0.1:8000` → `http://localhost:8000`
  - `NEXT_PUBLIC_WS_URL: ws://127.0.0.1:8000` → `ws://localhost:8000`
  - Reason: Windows Docker Desktop port forwarding resolves `localhost` correctly, not raw `127.0.0.1`

---

## System Architecture (v1 Stable)

```
┌─────────────────────────────────────────────┐
│           LOCAL (Docker Compose)             │
├─────────────────────────────────────────────┤
│ Frontend (Next.js 14)        :3000 ✅       │
│ Backend (FastAPI)            :8000 ✅       │
│ PostgreSQL 16 + pgvector     :5432 ✅       │
│ Valkey (Redis fork)          :6379 ✅       │
│ MinIO (S3-compatible)        :9000 ✅       │
└─────────────────────────────────────────────┘
            ↕ SSH Tunnel (port 41447)
┌─────────────────────────────────────────────┐
│      REMOTE (202.51.2.50)                   │
├─────────────────────────────────────────────┤
│ vLLM (Gemma 4 E4B-it)        :8100 ✅       │
│ ML Service (STT/TTS)         :5001 ✅       │
│  ├─ faster-whisper large-v3                 │
│  ├─ Piper TTS                               │
│  └─ Speaker embeddings                      │
└─────────────────────────────────────────────┘
```

---

## Startup Checklist

### Local
```bash
# Start all local services
docker-compose up -d

# Verify
curl http://localhost:8000/health
# Output: {"status":"ok","environment":"development","database":true,"valkey":true,"vllm":true,"ml_service":true}
```

### Remote SSH Tunnel
```bash
ssh -N -p 41447 \
  -L 8100:localhost:8100 \
  -L 5001:localhost:5001 \
  ekduiteen@202.51.2.50
```

### Test
1. Open http://localhost:3000
2. Sign in (demo or Google OAuth)
3. Complete onboarding
4. Go to **Teach** tab
5. Send audio → should process without WebSocket closing

---

## Files Changed in v1

| File | Change | Reason |
|------|--------|--------|
| `backend/services/routing_hooks.py` | Line 32: `dialect_hook` → `dialect_guess` | Fix AttributeError |
| `backend/services/response_orchestrator.py` | Lines 66-67: Removed non-existent attributes | Fix AttributeError |
| `docker-compose.yml` | Frontend env: `127.0.0.1` → `localhost` | Fix Docker Desktop port forwarding |

---

## Health Status

All services report healthy:
```json
{
  "status": "ok",
  "environment": "development",
  "database": true,
  "valkey": true,
  "vllm": true,
  "ml_service": true
}
```

---

## Known Limitations (v1)

None blocking. Current limitations are quality/UX, not infrastructure:
- ⚠️ STT quality variable (especially mixed Nepali/English)
- ⚠️ LLM sometimes too formal (Gemma 4)
- ⚠️ Voice quality acceptable but not premium

**These are Phase 2+ improvements, not blockers.**

---

## Next Phase (v2)

1. Fine-tune Qwen2.5-14B-Instruct-AWQ (target: better Nepali + code-switching)
2. Optimize STT for dialect variation
3. Improve voice naturalness (TTS tuning)
4. Performance optimization (inference latency)

---

## Git Commit

```
commit: Stable v1 - fix AttributeErrors and Docker port forwarding
  - routing_hooks.py: dialect_hook → dialect_guess
  - response_orchestrator.py: removed non-existent attributes
  - docker-compose.yml: localhost instead of 127.0.0.1
  
All services healthy. WebSocket stable. Production-ready local stack.
```

---

**Locked by:** Claude Code (Haiku 4.5)  
**Timestamp:** 2026-04-16T17:45:00Z  
**Status:** READY FOR DEPLOYMENT

---

## Post-v1 Verification Update — 2026-04-18

The codebase has since moved beyond the initial v1 stabilization work.

Verified activation changes now in the live codebase:
- approved corrections update persistent knowledge state
- approved correction rules are reused in future-session prompt guidance
- cross-session memory loads from durable DB snapshots
- low-trust extractions are queued for review instead of being learned directly
- single-teacher vocabulary confidence is capped until stronger validation

Verification notes:
- activation-specific backend checks are now passing
- one unrelated legacy backend test still fails in `test_intelligence_layer.py`

Verification-driven fixes applied after v1:
- `backend/db/connection.py` now supports SQLite test runs
- `backend/services/learning.py` now writes `vocabulary_teachers.created_at`
- `backend/services/learning.py` no longer depends on SQLite-incompatible `LEAST(...)`

This file remains the historical v1 release note; current operational truth is in:
- `README.md`
- `SYSTEM_STATUS_REPORT.md`
- `HANDOVER_TO_CODEX.md`
