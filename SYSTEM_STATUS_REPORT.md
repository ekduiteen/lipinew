# LIPI SYSTEM STATUS REPORT — 2026-04-18

## Executive Summary
✅ **SYSTEM OPERATIONAL**

The recent activation work is now verified in the codebase and in targeted runtime probes.

Verified activation state:
- approved corrections update persistent knowledge
- approved corrections become runtime-usable through approved `UsageRule` reload
- cross-session memory loads from durable snapshots at session start
- approved prior teachings are injected into prompt guidance
- low-trust extraction is blocked from direct learning and queued for review
- single-teacher vocabulary confidence is capped until multi-teacher reinforcement

---

## Activation Verification Matrix

| Check | Status | Proof |
|--------|--------|-------|
| Correction approval updates knowledge | ✅ PASS | Runtime-confirmed via isolated execution of `label_and_promote_to_gold()` |
| Correction approval influences future prompt/runtime | 🟡 PARTIAL | Code-confirmed read path; full live WS behavior not re-observed end-to-end |
| Cross-session memory loads | ✅ PASS | Runtime-confirmed via `load_teacher_long_term_memory()` probe |
| Approved teachings appear in prompt | ✅ PASS | Runtime-confirmed via `build_response_package()` probe |
| Low-trust extraction gets flagged/reviewed | ✅ PASS | Activation tests pass; validator and queue path confirmed |
| Single-teacher vocab confidence cap works | ✅ PASS | Runtime probe confirmed `0.70` with one teacher and `0.75` with two teachers |
| Moderation route works | ✅ PASS | Route and service confirmed; `GoldRecord` import issue fixed |
| Phrase variation frontend path works | 🟡 PARTIAL | Code-confirmed wiring; browser flow not replayed in this verification pass |
| Frontend backend URL assumptions fixed | ✅ PASS | Hardcoded backend URLs removed from frontend runtime paths |

---

## Test Execution Status

### Targeted backend verification

Command:
```bash
python -m pytest backend/tests/test_learning_activation.py backend/tests/test_learning.py backend/tests/test_intelligence_layer.py -q
```

Result:
- `22 passed`
- `1 failed`

Remaining failing test:
- `backend/tests/test_intelligence_layer.py::TestInputUnderstanding::test_detects_correction_code_switch_and_nuance_signals`
- Failure is unrelated to the activation work
- Current mismatch: expected `"en"` in `secondary_languages`, actual result is `["ne"]`

### Syntax verification

Command:
```bash
python -m compileall backend\services backend\routes backend\models backend\tests\test_learning_activation.py
```

Result:
- ✅ PASS

---

## Verification Fixes Applied During Audit

Two concrete blockers were found and fixed during verification:

### 1. SQLite test harness engine failure
File:
- `backend/db/connection.py`

Fix:
- avoid passing `pool_size` and `max_overflow` for SQLite URLs

Impact:
- backend activation tests now run instead of failing at import time

### 2. Vocabulary learning insert/runtime path
File:
- `backend/services/learning.py`

Fixes:
- `vocabulary_teachers` insert now writes `created_at`
- SQLite-incompatible `LEAST(...)` replaced with `CASE`

Impact:
- activation-specific tests and runtime confidence-cap probe now pass

---

## Current Runtime Health Notes

### Proven in runtime probes
- approval flow writes `knowledge_confidence_history`
- memory snapshots reload correctly
- approved rule block appears in turn guidance
- extraction validator rejects `script_mismatch`
- single-teacher confidence stays capped

### Still manual/live to confirm
- full end-to-end WebSocket reply quality change after approving a correction
- browser-exercised phrase variation flow with a real recording session

---

## Frontend Runtime Notes

The frontend proxy layer is now environment-driven:
- `frontend/lib/backend-url.ts` requires `BACKEND_URL` or `NEXT_PUBLIC_BACKEND_URL`
- browser pages use relative routes instead of hardcoded localhost URLs

Updated paths include:
- Phrase Lab
- Heritage
- auth proxy routes
- generic API proxy routes
- session creation route

---

## Current Engineering Status

| Area | Status | Notes |
|------|--------|-------|
| Backend activation loop | ✅ Verified | Core learning activation paths are now live |
| Test harness | ✅ Repaired | Activation tests execute |
| Documentation | ✅ Updated | README, handover, status, release note refreshed |
| Frontend proxying | ✅ Fixed | No hardcoded backend URLs remain in frontend runtime code |
| Unrelated legacy test | ⚠️ Open | `secondary_languages` expectation mismatch |

---

## Bottom Line

The activation work is real.

The correction loop is no longer inert, cross-session memory is no longer dead code, and the learning path is no longer gated only by raw STT confidence.
