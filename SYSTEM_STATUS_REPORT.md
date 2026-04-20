# LIPI SYSTEM STATUS REPORT — 2026-04-20

## Executive Summary
🟢 **SYSTEM RUNNING**

The platform is back in a healthy running state locally and remotely.

What changed on 2026-04-20:
- local app servers and local Docker services were restarted successfully
- remote Docker services were restarted successfully
- remote backend was repaired by rebuilding from current committed source
- remote compose was corrected to use localhost-published service bindings
- local and remote DB schemas were reconciled and stamped to Alembic head `f2a3b4c5d6e7`
- remote model routing was normalized around `127.0.0.1:8210`

Current runtime state:
- local frontend on `127.0.0.1:3000`: up
- local control dashboard on `127.0.0.1:3001`: up
- local backend on `127.0.0.1:8000`: healthy
- local tunnel:
  - `127.0.0.1:5001 -> remote 5001`
  - `127.0.0.1:8100 -> remote 8210`
  - `127.0.0.1:9000 -> remote 9000`
- remote backend on `127.0.0.1:8000`: healthy
- remote ML on `127.0.0.1:5001`: healthy
- remote model endpoint on `127.0.0.1:8210`: healthy

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
| Local stack startup on 2026-04-20 | ✅ PASS | Frontend, control dashboard, backend, Docker infra running |
| Remote backend health on 2026-04-20 | ✅ PASS | `{"status":"ok","environment":"development","database":true,"valkey":true,"vllm":true,"ml_service":true}` |
| Remote ML health on 2026-04-20 | ✅ PASS | `{"status":"ok","cuda_available":true,...}` |
| Remote model endpoint on 2026-04-20 | ✅ PASS | `curl http://127.0.0.1:8210/v1/models` succeeded |
| Local and remote Alembic head | ✅ PASS | both `alembic_version.version_num = f2a3b4c5d6e7` |

## Runtime / Operations Findings

### Remote backend root cause

The remote backend restart loop was caused by process drift, not an application-only bug:
- remote `/data/lipi` was an old source snapshot, not a git checkout
- the remote backend image was behind the repo
- remote compose had `DATABASE_URL` hardcoded to a stale Postgres container IP

Fix applied:
- current committed backend source was synced to remote
- remote backend image was rebuilt
- remote compose was corrected so backend uses `127.0.0.1` bindings for Postgres, Valkey, MinIO, and ML

### Schema state

Both DBs were drifted legacy environments and could not be advanced safely by a naive `alembic upgrade head`.

Repair outcome:
- head-era missing tables were created where needed
- moderation claim columns and indexes were added
- `admin_keyterm_seeds` bootstrap data was inserted
- both DBs now report Alembic revision `f2a3b4c5d6e7`

Operational rule from here:
- future schema changes should go through Alembic only
- do not mix `init-db.sql`, ORM `create_all`, and Alembic on an existing DB

## Current Engineering Status

| Area | Status | Notes |
|------|--------|-------|
| Backend activation loop | ✅ Verified | Core learning activation paths are live |
| Admin control backend | ✅ Verified | Claims, filtering, batching, metrics, export download all added |
| Control frontend | ✅ Verified | Build passes, download path works |
| Test harness | ✅ Repaired | Activation and control tests execute |
| Runtime operations | ✅ Repaired | Remote compose and deploy path now match the real host |
| Documentation | ✅ Updated | Docs now describe `:8210`, localhost bindings, and the repeatable deploy loop |

## Bottom Line

The platform is healthy now, but the real lesson is procedural:
- remote deploys must sync committed source deliberately
- remote backend must target localhost-published services
- schema changes need migration discipline

If that process is followed, the current setup is repeatable.
