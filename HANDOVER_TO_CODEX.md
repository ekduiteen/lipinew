# LIPI Handover — April 20, 2026

This is the current engineer handover. Update this file when state changes.

## Current Status

| Layer | Status | Notes |
|-------|--------|-------|
| Backend | ✅ Running | Local and remote backend healthy |
| Database | ✅ Running | Local and remote DB healthy; reconciled to head |
| Frontend | ✅ Running | Local app serving on `:3000` |
| Control Frontend | ✅ Running | Local admin dashboard serving on `:3001` |
| WebSocket Teach Loop | ✅ Healthy | Runtime path verified |
| Turn Intelligence | ✅ Healthy | Intent, entities, keyterms, repair, dashboard visibility live |
| Phrase Lab | ✅ Healthy | Primary + variation route wiring present |
| Heritage | ✅ Healthy | Uses proxied backend routes |
| Verification Harness | ✅ Improved | Activation and admin-control tests pass |

## What Was Just Completed

### Runtime / ops repair
- local stack restarted cleanly
- remote stack restarted cleanly
- remote backend is healthy on `127.0.0.1:8000`
- remote ML is healthy on `127.0.0.1:5001`
- remote model path is healthy through `127.0.0.1:8210`
- local hybrid tunnel is:
  - local `5001 -> remote 5001`
  - local `8100 -> remote 8210`
  - local `9000 -> remote 9000`

### Remote backend root-cause fix
- remote `/data/lipi` was not a git checkout; it was a source snapshot
- remote backend image was rebuilt from current committed backend source
- remote compose was repaired so backend uses localhost-published infra bindings
- the real backend blocker was a stale hardcoded Postgres container IP in remote `DATABASE_URL`
- remote compose now uses `127.0.0.1:5432` for Postgres, not an ephemeral Docker IP

### Schema reconciliation
- local and remote schemas were reconciled to match head-era expectations
- missing head-era tables were created where needed
- `review_queue_items.claimed_by` and `claimed_at` were added on both DBs
- indexes and `admin_keyterm_seeds` bootstrap data were added
- local and remote `alembic_version` now both read `f2a3b4c5d6e7`

### Local dev fixes
- `backend/.dockerignore` excludes transient pytest temp directories that broke Docker builds
- `docker-compose.dev.yml` mounts repo `.env` into the backend container
- `docker-compose.dev.yml` excludes transient pytest temp directories from Uvicorn reload watching
- when running hybrid local dev with a local backend, do not tunnel remote `:8000` onto local `:8000`

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
- pass

## Important Operational Truths

- remote compose path is `/data/lipi/docker-compose.lipi.yml`
- remote backend target for LLM traffic is `http://127.0.0.1:8210`
- local tunnel keeps `8100` only as a local convenience port mapped to remote `8210`
- remote backend depends on localhost-published Postgres, Valkey, MinIO, and ML bindings
- remote `/data/lipi` should be treated as a synced snapshot, not a live git checkout

## Development / Deploy Rule

Going forward, the stable loop is:

1. Develop locally with local backend on `:8000`.
2. Tunnel only remote ML/model/minio when needed.
3. Commit backend changes before deploy.
4. Sync committed source to remote `/data/lipi`.
5. Rebuild remote backend image.
6. Verify remote `/health`, ML `/health`, and `:8210/v1/models`.
7. For schema changes, use Alembic only; do not mix `create_all` or silent init paths into an existing DB.

## Remaining Limits

- snapshot creation is synchronous and request-bound
- live WS reply quality shift after approved correction is still only partially re-observed end-to-end
- production MinIO artifact download should still be smoke-tested against the real bucket after deploy
- the remote compose file remains an ops-managed artifact and can drift if edited directly on-host without updating the documented process

## Bottom Line

The system is running, the remote deploy path is understood, and the main operational risk now is process drift rather than an unknown infrastructure bug.
