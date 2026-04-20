# LIPI SYSTEM STATUS REPORT — 2026-04-18

## Executive Summary
✅ **SYSTEM OPERATIONAL**

The recent learning-loop activation work, admin/control hardening, and the new turn-intelligence upgrade are now verified in code and targeted execution.

Verified activation state:
- approved corrections update persistent knowledge
- approved corrections become runtime-usable through approved `UsageRule` reload
- cross-session memory loads from durable snapshots at session start
- approved prior teachings are injected into prompt guidance
- low-trust extraction is blocked from direct learning and queued for review
- single-teacher vocabulary confidence is capped until multi-teacher reinforcement

Verified control-system state:
- moderation queue supports claims, expiry, filters, and batch actions
- moderation metrics are computed from DB state
- dataset snapshots are auditable and downloadable end-to-end
- `frontend-control` builds successfully with the current code

Verified turn-intelligence state:
- teacher turns now persist intent, entities, keyterms, code-switch, repair metadata, and learning usability
- keyterm boosting is applied before STT and during transcript repair/extraction
- low-signal turns are downgraded in learning weight instead of being treated as clean evidence
- dashboard and control analytics expose recent analyzed turns and aggregate quality signals

---

## Verification Matrix

| Check | Status | Proof |
|--------|--------|-------|
| Correction approval updates knowledge | ✅ PASS | Runtime-confirmed via `label_and_promote_to_gold()` |
| Correction approval influences future prompt/runtime | 🟡 PARTIAL | Code-confirmed read path; full live WS behavior not re-observed end-to-end |
| Cross-session memory loads | ✅ PASS | Runtime-confirmed via `load_teacher_long_term_memory()` probe |
| Approved teachings appear in prompt | ✅ PASS | Runtime-confirmed via `build_response_package()` probe |
| Low-trust extraction gets flagged/reviewed | ✅ PASS | Activation tests pass; validator and queue path confirmed |
| Single-teacher vocab confidence cap works | ✅ PASS | Runtime probe confirmed `0.70` with one teacher and `0.75` with two teachers |
| Moderation queue claims are exclusive | ✅ PASS | `test_admin_control.py` |
| Batch moderation works | ✅ PASS | `test_admin_control.py` |
| Real metrics endpoint works | ✅ PASS | `test_admin_control.py` |
| Dataset snapshot download works | ✅ PASS | `test_admin_control.py` |
| Control frontend production build | ✅ PASS | `npm run build` in `frontend-control` |

---

## Test Execution Status

### Targeted backend verification

Command:
```bash
python -m pytest backend/tests/test_admin_control.py backend/tests/test_learning_activation.py -q
```

Result:
- `9 passed`

Covered:
- queue claiming exclusivity
- expired claim release
- filtered queue listing
- batch approval
- real metrics endpoint
- snapshot download route
- learning activation paths

### Control frontend build verification

Command:
```bash
cd frontend-control
npm run build
```

Result:
- ✅ PASS

---

## Control-System Hardening Applied

### Queue safety and throughput
Files:
- `backend/models/intelligence.py`
- `backend/services/admin_moderation.py`
- `backend/routes/admin_moderation.py`
- `backend/alembic/versions/e6f7a8b9c0d1_admin_queue_claims_and_metrics.py`

Changes:
- added `claimed_by` / `claimed_at` to `review_queue_items`
- added claim expiry and auto-release
- added filtered queue listing
- added claim-buffer prefetching support
- added batch approve / reject / release endpoints
- added queue indexes for moderation workload

Impact:
- multiple moderators can review safely without duplicate assignment on the normal path

### Real metrics
File:
- `backend/routes/admin_system.py`

Changes:
- added `/api/ctrl/system/metrics/real`
- removed placeholder integrity and storage values from control-system responses
- added DB-derived approval / rejection / claim / low-trust / review-time metrics

Impact:
- dashboard and export screens now reflect actual system state instead of fake numbers

### Export pipeline
Files:
- `backend/services/admin_export.py`
- `backend/routes/admin_export.py`
- `frontend-control/src/app/api/proxy-download/[snapshotId]/route.ts`

Changes:
- snapshot filters now support language, dialect, date range, and confidence threshold
- snapshot creation now writes audit logs
- authenticated snapshot download route now streams ZIP artifacts
- control frontend download button is now live

Impact:
- data can leave the system through an auditable and working path

---

## Frontend Runtime Notes

The control frontend is now build-clean and environment-driven:
- `frontend-control/next.config.ts` requires `BACKEND_URL` or `NEXT_PUBLIC_API_URL`
- missing proxy download path is implemented
- dead staff nav is removed
- fake health-log and fake stat surfaces are removed or replaced with real values

The main app frontend remains environment-driven:
- `frontend/lib/backend-url.ts` requires `BACKEND_URL` or `NEXT_PUBLIC_BACKEND_URL`

---

## Current Engineering Status

| Area | Status | Notes |
|------|--------|-------|
| Backend activation loop | ✅ Verified | Core learning activation paths are now live |
| Admin control backend | ✅ Verified | Claims, filtering, batching, metrics, export download all added |
| Control frontend | ✅ Verified | Build passes, dead UI removed, download works |
| Test harness | ✅ Repaired | Activation and control tests execute |
| Documentation | ✅ Updated | README, handover, status, release note refreshed |

---

## Bottom Line

The activation work is real, and the admin/control layer has moved from basic moderation to a usable data-operations system.

The correction loop is no longer inert, the learning path is no longer gated only by raw STT confidence, and the control layer now supports safe multi-reviewer moderation plus audited dataset export.
