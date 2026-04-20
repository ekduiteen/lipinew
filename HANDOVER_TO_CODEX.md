# LIPI Handover — April 18, 2026

This is the current engineer handover. Update this file when state changes.

## Current Status

| Layer | Status | Notes |
|-------|--------|-------|
| Backend | ✅ Healthy | Activation loop verified and testable |
| Database | ✅ Healthy | Control migration added for queue claims and moderation indexes |
| Frontend | ✅ Healthy | Backend URL assumptions removed from runtime paths |
| Control Frontend | ✅ Healthy | Builds successfully and reflects real moderation/export state |
| WebSocket Teach Loop | ✅ Healthy | Memory + approved-rule read path wired at session start |
| Turn Intelligence | ✅ Healthy | Intent, entities, keyterms, repair, and dashboard visibility are live |
| Phrase Lab | ✅ Healthy | Primary + variation route wiring present |
| Heritage | ✅ Healthy | Uses proxied backend routes |
| Verification Harness | ✅ Improved | Activation and admin-control tests pass |

---

## What Was Just Completed

### Learning activation state
- approved corrections update persistent knowledge
- approved correction rules are readable in future sessions
- cross-session memory loads from durable snapshots
- approved prior teachings appear in prompt guidance
- low-trust extractions are diverted to review instead of direct learning
- single-teacher vocabulary confidence is capped at `0.70` until stronger validation

### Turn-intelligence state
- `backend/services/keyterm_service.py` prepares per-turn candidates from memory, teacher history, admin seeds, and uncertain review items
- `backend/services/transcript_repair.py` performs cautious low-confidence repair using those candidates
- `backend/services/turn_intelligence.py` persists canonical turn analysis into `message_analysis` and `message_entities`
- the live WS path consumes the cheap analysis; the async learning worker can enrich the same turn authoritatively
- `/api/dashboard/overview` and `/api/ctrl/system/intelligence/overview` expose aggregate intent/entity/keyterm quality signals

### Admin/control hardening state
- queue claiming with expiry and auto-release
- filtered moderation queue by review type, language, confidence, source, and age
- batch approve / reject / release actions
- real moderation metrics endpoint
- audited dataset snapshot creation with richer filters
- authenticated control-frontend download path
- moderation UI surfaces review type, source, confidence, teacher credibility, and supporting-teacher signal
- gold browser surfaces provenance and confidence history

---

## Current Test State

Command:
```bash
python -m pytest backend/tests/test_admin_control.py backend/tests/test_learning_activation.py -q
```

Result:
- `9 passed`

Command:
```bash
cd frontend-control
npm run build
```

Result:
- ✅ PASS

---

## Important Files

### Activation loop
- `backend/services/admin_moderation.py`
- `backend/services/correction_graph.py`
- `backend/services/learning.py`
- `backend/services/memory_service.py`
- `backend/services/response_orchestrator.py`
- `backend/routes/sessions.py`

### Turn intelligence
- `backend/services/keyterm_service.py`
- `backend/services/transcript_repair.py`
- `backend/services/intent_classifier.py`
- `backend/services/entity_extractor.py`
- `backend/services/turn_intelligence.py`
- `backend/tests/test_turn_intelligence.py`
- `backend/alembic/versions/f2a3b4c5d6e7_turn_intelligence_layer.py`

### Admin / control
- `backend/routes/admin_moderation.py`
- `backend/routes/admin_system.py`
- `backend/routes/admin_export.py`
- `backend/services/admin_export.py`
- `backend/models/intelligence.py`
- `backend/alembic/versions/e6f7a8b9c0d1_admin_queue_claims_and_metrics.py`
- `backend/tests/test_admin_control.py`

### Control frontend
- `frontend-control/next.config.ts`
- `frontend-control/src/app/(dashboard)/moderation/page.tsx`
- `frontend-control/src/app/(dashboard)/dashboard/page.tsx`
- `frontend-control/src/app/(dashboard)/exports/page.tsx`
- `frontend-control/src/app/(dashboard)/gold-records/page.tsx`
- `frontend-control/src/app/(dashboard)/health/page.tsx`
- `frontend-control/src/app/api/proxy-download/[snapshotId]/route.ts`

---

## Remaining Limits

These are still true after the hardening work:
- snapshot creation is synchronous and request-bound
- live WS reply quality shift after approved correction is still only partially re-observed end-to-end
- production MinIO artifact download should still be smoke-tested against the real bucket after deploy

These are scale/ops limits, not broken paths.

---

## Bottom Line

The activation work is real, and the admin/control layer is now a functioning data-operations system rather than a thin moderation UI.
