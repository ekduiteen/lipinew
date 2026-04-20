# LIPI Operations

Operational reference for the actual current LIPI runtime.

## Current Reality

### Local
- `frontend` on `http://127.0.0.1:3000`
- `backend` on `http://127.0.0.1:8000`
- `frontend-control` on `http://127.0.0.1:3001`
- `postgres`, `valkey`, `minio` in Docker

### Remote
- one NVIDIA L40S
- live compose path: `/data/lipi/docker-compose.lipi.yml`
- remote backend on `127.0.0.1:8000`
- remote ML on `127.0.0.1:5001`
- remote model proxy on `127.0.0.1:8210`
- Docker services: `backend`, `ml`, `postgres`, `valkey`, `minio`

### Current state snapshot
- as of `2026-04-20`, local stack is up
- as of `2026-04-20`, remote stack is up
- local backend health is `ok`
- remote backend health is `ok`
- remote ML health is `ok`
- remote backend uses `VLLM_URL=http://127.0.0.1:8210`
- remote `:8100` is not the canonical backend target
- local and remote DBs were reconciled and stamped to Alembic head `f2a3b4c5d6e7`

## Canonical Health Checks

### Local
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:3000
curl http://127.0.0.1:3001
docker compose ps
```

### Remote
```bash
ssh -p 41447 ekduiteen@202.51.2.50
cd /data/lipi
docker compose -f docker-compose.lipi.yml ps
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5001/health
curl http://127.0.0.1:8210/v1/models
ss -ltnp | grep -E ':8210|:5001|:8000|:5432|:6379|:9000'
```

## Local Operations

### Start local stack
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres valkey minio minio-init backend frontend
```

### Start local control dashboard
```bash
cd frontend-control
node_modules\.bin\next.cmd dev --port 3001
```

### Restart local services
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart postgres
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart valkey
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart minio
```

### Rebuild local app services
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build backend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build frontend
```

### Stop local stack
```bash
docker compose down
```

## Remote Operations

### SSH
```bash
ssh -p 41447 ekduiteen@202.51.2.50
cd /data/lipi
```

### Restart remote Docker services
```bash
docker compose -f docker-compose.lipi.yml restart postgres
docker compose -f docker-compose.lipi.yml restart valkey
docker compose -f docker-compose.lipi.yml restart minio
docker compose -f docker-compose.lipi.yml restart ml
docker compose -f docker-compose.lipi.yml restart backend
```

### Rebuild remote Docker services
```bash
docker compose -f docker-compose.lipi.yml up -d --build backend
docker compose -f docker-compose.lipi.yml up -d --build ml
```

### Remote logs
```bash
docker compose -f docker-compose.lipi.yml logs -f backend
docker compose -f docker-compose.lipi.yml logs -f ml
docker compose -f docker-compose.lipi.yml logs -f postgres
docker compose -f docker-compose.lipi.yml logs -f valkey
docker compose -f docker-compose.lipi.yml logs -f minio
```

## Remote Runtime Constraints

The remote host is not a live git checkout. `/data/lipi` is an ops-managed source snapshot.

Treat these as non-negotiable until the deployment model changes:
- sync committed source to remote deliberately
- rebuild the remote image after sync
- do not assume `git pull` on the remote host will work
- do not point backend `DATABASE_URL` at an ephemeral container IP
- do not point backend `VLLM_URL` at `:8100` unless the remote model topology is deliberately changed

### Known-good remote compose pattern

The remote backend currently relies on host-mode networking and localhost-published infra bindings:
- backend `network_mode: host`
- postgres published on `127.0.0.1:5432`
- valkey published on `127.0.0.1:6379`
- minio published on `127.0.0.1:9000` and `:9001`
- ml published on `127.0.0.1:5001`
- backend env points to `127.0.0.1`, not container IPs

Critical env values on remote:
```bash
DATABASE_URL=postgresql+asyncpg://lipi:...@127.0.0.1:5432/lipi
VALKEY_URL=valkey://127.0.0.1:6379/0
MINIO_ENDPOINT=127.0.0.1:9000
ML_SERVICE_URL=http://127.0.0.1:5001
VLLM_URL=http://127.0.0.1:8210
```

## Tunnel / Hybrid Dev

When running a local backend, do not forward remote `:8000` onto local `:8000`.

```bash
ssh -N -p 41447 \
  -L 5001:localhost:5001 \
  -L 8100:localhost:8210 \
  -L 9000:localhost:9000 \
  ekduiteen@202.51.2.50
```

Then verify:
```bash
curl http://127.0.0.1:5001/health
curl http://127.0.0.1:8100/v1/models
curl http://127.0.0.1:8000/health
```

## Repeatable Development Loop

Use this while actively building features:

1. Start local Docker infra and local backend/frontend.
2. Start `frontend-control` locally on `:3001` if needed.
3. Open the SSH tunnel for remote ML/model only.
4. Keep local backend on local `:8000`.
5. Verify local backend plus tunneled remote model health.
6. If health fails, check local backend logs first, then remote ML/model health.

## Repeatable Remote Deploy Loop

Use this after committed backend or infra changes:

1. Commit the backend changes you intend to deploy.
2. Sync committed source to remote `/data/lipi`.
3. Rebuild the remote backend image.
4. Restart remote backend and any changed services.
5. Verify backend `/health`, ML `/health`, and `:8210/v1/models`.
6. If backend fails, inspect remote backend logs before changing code again.

### Recommended sync command

For backend-oriented deploys, sync the committed tree instead of copying an arbitrary dirty worktree:

```bash
git archive --format=tar HEAD backend ml scripts init-db.sql .env.example | \
ssh -p 41447 ekduiteen@202.51.2.50 "mkdir -p /data/lipi && tar -xf - -C /data/lipi"
```

If the remote compose file itself changes, update `/data/lipi/docker-compose.lipi.yml` explicitly as a separate ops step.

## Schema / Migration Discipline

Current legacy reality:
- these DBs were previously baseline-stamped against drifted schemas
- `init-db.sql`, ORM `create_all`, and Alembic were mixed historically
- reconciliation to head `f2a3b4c5d6e7` required manual repair

Development rule going forward:
- after this point, schema changes should go through Alembic only
- do not silently rely on `init-db.sql` or ad-hoc `create_all` against an existing DB
- if a future environment drifts, treat it as a reconciliation task, not a normal upgrade

Verification commands:
```bash
docker compose exec -T postgres psql -U lipi -d lipi -c "SELECT version_num FROM alembic_version;"
ssh -p 41447 ekduiteen@202.51.2.50 "cd /data/lipi && docker compose -f docker-compose.lipi.yml exec -T postgres psql -U lipi -d lipi -c 'SELECT version_num FROM alembic_version;'"
```

## Common Checks

### Backend healthy but Teach still broken
Check:
1. `curl http://127.0.0.1:8000/health`
2. `curl http://127.0.0.1:5001/health`
3. `curl http://127.0.0.1:8100/v1/models`
4. `docker compose -f docker-compose.yml -f docker-compose.dev.yml logs backend --tail 80`

### Remote backend restart loop
Usually one of:
- stale backend image versus current source
- remote compose drift
- backend env pointing to stale container IPs instead of localhost-published services

Check:
```bash
ssh -p 41447 ekduiteen@202.51.2.50
cd /data/lipi
docker compose -f docker-compose.lipi.yml ps -a
docker compose -f docker-compose.lipi.yml logs --tail 200 backend
```

## Canonical Docs

- [README.md](README.md)
- [CLAUDE.md](CLAUDE.md)
- [DEV_ONBOARDING.md](DEV_ONBOARDING.md)
- [HANDOVER_TO_CODEX.md](HANDOVER_TO_CODEX.md)
