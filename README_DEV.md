# LIPI — Local Development Setup

> Read [CLAUDE.md](CLAUDE.md) first. It is the engineering source of truth.

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker + Compose v2 | 24+ | Required |
| NVIDIA driver | 535+ | For GPU services (vLLM, ml) |
| nvidia-container-toolkit | latest | GPU passthrough to Docker |
| Node.js | 20+ | Frontend dev outside Docker (optional) |
| Python | 3.11 | Backend/ml dev outside Docker (optional) |
| GPUs | 2× L40S (or equivalent 48GB) | For full Qwen3-32B + STT/TTS |

CPU-only mode: comment out `vllm` and `ml` services in `docker-compose.yml` and use the Groq fallback (`GROQ_API_KEY` required).

## First-time setup

```bash
# 1. Clone & enter
git clone <repo> lipi && cd lipi

# 2. Copy env template and fill in secrets
cp .env.example .env
# edit .env: POSTGRES_PASSWORD, MINIO_*, JWT_SECRET, GROQ_API_KEY, GOOGLE_*, CADDY_DOMAIN

# 3. Verify GPU passthrough
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi

# 4. Bring up infra services first (fast)
docker compose up -d postgres valkey minio minio-init

# 5. Then GPU services (vLLM ~5min cold start, ml ~2min)
docker compose up -d vllm ml

# 6. Then app services
docker compose up -d backend frontend caddy
```

## Health checks

```bash
curl http://localhost:8000/health    # backend → checks db, valkey, vllm, ml
curl http://localhost:5001/health    # ml service → STT/TTS load state
curl http://localhost:8080/v1/models # vLLM → should list "lipi"
```

All four should report healthy before testing the conversation flow.

## Service ports

| Service  | Port | Purpose |
|----------|------|---------|
| caddy    | 80, 443 | Reverse proxy (only public entry) |
| frontend | 3000 | Next.js |
| backend  | 8000 | FastAPI REST + WebSocket |
| ml       | 5001 | STT + TTS |
| vllm     | 8080 | OpenAI-compatible LLM API |
| postgres | 5432 | Database |
| valkey   | 6379 | Cache (NOT Redis) |
| minio    | 9000, 9001 | Object storage + console |

## Working on a single service

Frontend hot reload (outside Docker):
```bash
cd frontend && npm install && npm run dev
```

Backend hot reload (outside Docker):
```bash
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Both still need the dockerized infra (`postgres`, `valkey`, `vllm`, `ml`) running.

## Database

Schema is loaded from `init-db.sql` on first `postgres` container start. To reset:
```bash
docker compose down -v   # WARNING: wipes all volumes
docker compose up -d postgres
```

Connect with psql:
```bash
docker compose exec postgres psql -U lipi -d lipi
```

## Common issues

- **vLLM OOM**: lower `--gpu-memory-utilization` in `docker-compose.yml`, or reduce `--max-model-len`.
- **ml service can't find CUDA**: confirm `nvidia-container-toolkit` installed and Docker daemon restarted.
- **Caddy cert errors locally**: uncomment `local_certs` in `Caddyfile` for self-signed certs.
- **`from redis import ...` errors**: never. Use `from valkey.asyncio import Valkey`. Redis is SSPL-licensed.

## Build order

The Phase 0 → 3 build plan lives in [CLAUDE.md](CLAUDE.md). Don't deviate.
