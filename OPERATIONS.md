# LIPI Operations

Operational reference for the **actual current LIPI runtime**, not the old multi-GPU / Kubernetes plan.

## Current Reality

### Local
- `frontend` on `http://127.0.0.1:3000`
- `backend` on `http://127.0.0.1:8000`
- `postgres`, `valkey`, `minio` in Docker

### Remote
- one NVIDIA L40S
- host-level Gemma OpenAI-compatible server on `127.0.0.1:8100`
- Docker `backend`, `ml`, `postgres`, `valkey`, `minio`
- live remote compose path: `/data/lipi/docker-compose.lipi.yml`

### Model stack
- **LLM**: Gemma 4
- **STT**: faster-whisper large-v3
- **TTS**: Piper

## Canonical Health Checks

### Local
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:3000
docker compose ps
```

### Remote
```bash
ssh -p 41447 ekduiteen@202.51.2.50
cd /data/lipi
docker compose -f docker-compose.lipi.yml ps
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5001/health
curl http://127.0.0.1:8100/v1/models
```

## Local Operations

### Start local stack
```bash
docker compose up -d postgres valkey minio minio-init backend frontend
```

### Restart local services
```bash
docker compose restart backend
docker compose restart frontend
docker compose restart postgres
docker compose restart valkey
docker compose restart minio
```

### Rebuild local app services
```bash
docker compose up -d --build backend
docker compose up -d --build frontend
docker compose up -d --build ml
```

### Local logs
```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
docker compose logs -f valkey
docker compose logs -f minio
```

## Remote Operations

### SSH
```bash
ssh -p 41447 ekduiteen@202.51.2.50
cd /data/lipi
```

### Restart remote Docker services
```bash
docker compose -f docker-compose.lipi.yml restart backend
docker compose -f docker-compose.lipi.yml restart ml
docker compose -f docker-compose.lipi.yml restart postgres
docker compose -f docker-compose.lipi.yml restart valkey
docker compose -f docker-compose.lipi.yml restart minio
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

## Host-Level Gemma Service

Gemma is not managed by the main remote compose file. It runs as a host-level process on `:8100`.

### Check Gemma
```bash
curl http://127.0.0.1:8100/v1/models
```

### If Gemma is down
Check the custom server process and restart it from the host shell using the current launcher script:
```bash
python scripts/gemma_openai_server.py
```

If you change Gemma model/runtime behavior, update:
- [scripts/gemma_openai_server.py](scripts/gemma_openai_server.py)
- [DEV_ONBOARDING.md](DEV_ONBOARDING.md)

## Tunnel / Hybrid Dev

When running the frontend locally against remote inference/backend services:

```bash
ssh -N -p 41447 \
  -L 8000:localhost:8000 \
  -L 5001:localhost:5001 \
  -L 8100:localhost:8100 \
  -L 9000:localhost:9000 \
  ekduiteen@202.51.2.50
```

Then verify:
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5001/health
curl http://127.0.0.1:8100/v1/models
```

## Data Services

### Postgres
```bash
docker compose exec postgres psql -U lipi -d lipi
```

### Valkey
```bash
docker compose exec valkey valkey-cli
```

### MinIO
```bash
docker compose logs minio --tail 50
```

## Common Checks

### Backend healthy but Teach still broken
Check:
1. `curl http://127.0.0.1:8000/health`
2. `curl http://127.0.0.1:5001/health`
3. `curl http://127.0.0.1:8100/v1/models`
4. `docker compose logs backend --tail 80`

### Frontend loads but data does not
Usually means:
- local `:3000` is fine
- backend on `:8000` is not reachable or not the expected service

### TTS feels wrong
Check:
- current Piper voice id in `ml/tts.py`
- whether English/Nepali split routing is actually deployed remotely

### STT is weak on Newari / mixed speech
This is still a known product limitation, not just an ops issue.

## Current Known Weak Spots

- Newari and mixed-language STT quality
- voice feel and language-specific TTS quality
- rigid response delivery despite stronger backend planning

Those are product-quality issues. Don’t mistake them for infra breakage unless health checks fail.

## Canonical Docs

- [README.md](README.md)
- [CLAUDE.md](CLAUDE.md)
- [DEV_ONBOARDING.md](DEV_ONBOARDING.md)
- [HANDOVER_TO_CODEX.md](HANDOVER_TO_CODEX.md)
