# LIPI Handover — April 18, 2026

This is the current engineer handover. Update this file when state changes.

## Current Status

| Layer | Status | Notes |
|-------|--------|-------|
| Backend | ✅ Healthy | Activation loop verified and testable |
| Database | ✅ Healthy | Migration added for vocabulary reliability |
| Frontend | ✅ Healthy | Backend URL assumptions removed from runtime paths |
| WebSocket Teach Loop | ✅ Healthy | Memory + approved-rule read path wired at session start |
| Phrase Lab | ✅ Healthy | Primary + variation route wiring present |
| Heritage | ✅ Healthy | Uses proxied backend routes |
| Verification Harness | ✅ Improved | SQLite engine/test blocker fixed |

---

## What Was Just Verified

The recent activation work is now real, not dormant:
- approved corrections update persistent knowledge
- approved correction rules are readable in future sessions
- cross-session memory loads from durable snapshots
- approved prior teachings appear in prompt guidance
- low-trust extractions are diverted to review instead of direct learning
- single-teacher vocabulary confidence is capped at `0.70` until stronger validation

Runtime-confirmed:
- `label_and_promote_to_gold()` approval side effects
- `load_teacher_long_term_memory()` snapshot reload
- approved rule injection into `build_response_package()`
- extraction validator behavior
- vocab confidence cap behavior

---

## Verification Fixes Applied

### Test harness fix
File:
- `backend/db/connection.py`

Change:
- SQLite URLs no longer receive `pool_size` / `max_overflow`

Why:
- pytest collection was failing before any activation tests ran

### Learning runtime fix
File:
- `backend/services/learning.py`

Changes:
- `vocabulary_teachers.created_at` is now written explicitly
- SQLite-incompatible `LEAST(...)` removed from vocab update SQL

Why:
- isolated runtime probe exposed a real failure in the confidence-cap path

---

## Current Test State

Command:
```bash
python -m pytest backend/tests/test_learning_activation.py backend/tests/test_learning.py backend/tests/test_intelligence_layer.py -q
```

Result:
- `22 passed`
- `1 failed`

Remaining failure:
- `backend/tests/test_intelligence_layer.py::TestInputUnderstanding::test_detects_correction_code_switch_and_nuance_signals`
- unrelated to the activation work

---

## Important Files

### Activation loop
- `backend/services/admin_moderation.py`
- `backend/services/correction_graph.py`
- `backend/services/learning.py`
- `backend/services/memory_service.py`
- `backend/services/response_orchestrator.py`
- `backend/routes/sessions.py`

### Verification coverage
- `backend/tests/test_learning_activation.py`

### Frontend route fixes
- `frontend/lib/backend-url.ts`
- `frontend/app/api/proxy/[...path]/route.ts`
- `frontend/app/api/heritage/[...path]/route.ts`
- `frontend/app/(tabs)/phrase-lab/page.tsx`
- `frontend/app/(tabs)/heritage/page.tsx`

---

## Current Open Items

These are still not fully re-proven in a live browser or full WS loop:
- visible reply-quality change after approving a correction and starting a fresh live session
- browser-exercised phrase variation flow with real audio

These are verification gaps, not codepath gaps.

---

## Bottom Line

The activation work is in place, verified, and no longer blocked by the test harness.
