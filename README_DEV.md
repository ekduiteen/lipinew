# LIPI — Local Development Setup

> Read [CLAUDE.md](CLAUDE.md) first. It is the engineering source of truth.

## Architecture: Local + Remote

**Local (your machine):**
- Frontend (Next.js via `npm run dev` on port 3000)
- Backend (FastAPI in Docker on port 8000)
- Database, Cache, Storage (postgres, valkey, minio in Docker)

**Remote (GPU server):**
- vLLM (Qwen2.5-14B on port 8100)
- ML Service (STT + TTS on port 5001)

They connect via SSH tunneling or direct network access to the remote server.

---

## Prerequisites

| Tool | Version | Location |
|------|---------|----------|
| Docker + Compose v2 | 24+ | Local machine |
| Node.js | 20+ | Local machine |
| SSH access | - | Remote server (GPU host) |
| NVIDIA driver | 535+ | **Remote server only** |
| CUDA 12.1+ | - | **Remote server only** |

You do NOT need GPU on your local machine. Use Groq fallback if remote services are unavailable.

---

## First-time setup

### 1. Local machine: Clone & configure

```bash
git clone <repo> lipi && cd lipi
cp .env.example .env
# edit .env with:
#   - POSTGRES_PASSWORD (secure)
#   - MINIO_ACCESS_KEY, MINIO_SECRET_KEY
#   - JWT_SECRET (secure)
#   - GROQ_API_KEY (for fallback)
#   - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
#   - VLLM_URL=http://localhost:8100 (via SSH tunnel)
#   - ML_SERVICE_URL=http://localhost:5001 (via SSH tunnel)
```

### 2. Remote server: Start vLLM (one-time)

SSH into the remote server and run:

```bash
# Install vLLM
pip install vllm torch

# Start vLLM on port 8100
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-14B-Instruct-AWQ \
  --dtype auto \
  --gpu-memory-utilization 0.85 \
  --port 8100 \
  --enable-prefix-caching \
  --max-model-len 8192 \
  --served-model-name lipi

# Keep this running — use screen or systemd service for production
```

### 3. Remote server: Start ML service (STT + TTS)

In another terminal on the remote server:

```bash
cd lipi/ml
python -m pip install -r requirements.txt
python main.py
# Listens on port 5001
```

### 4. Local machine: SSH tunnel to remote

```bash
# In a terminal, keep this running
ssh -L 8100:localhost:8100 -L 5001:localhost:5001 user@remote-server

# Now your local machine can access:
# - http://localhost:8100 → remote vLLM
# - http://localhost:5001 → remote ML service
```

### 5. Local machine: Bring up local Docker services

```bash
docker compose up -d postgres valkey minio minio-init backend
```

### 6. Local machine: Start frontend

```bash
cd frontend
npm install
npm run dev
# Opens on http://localhost:3000
```

---

## Health checks

```bash
# Local backend (should report all services healthy)
curl http://localhost:8000/health

# Remote vLLM
curl http://localhost:8100/v1/models

# Remote ML service
curl http://localhost:5001/health
```

## Service ports

| Service  | Port | Location |
|----------|------|----------|
| frontend | 3000 | Local (npm dev) |
| backend  | 8000 | Local Docker |
| postgres | 5432 | Local Docker (internal only) |
| valkey   | 6379 | Local Docker (internal only) |
| minio    | 9000 | Local Docker |
| vllm     | 8100 | **Remote** (SSH tunneled to 8100) |
| ml       | 5001 | **Remote** (SSH tunneled to 5001) |

---

## Working on a single service

### Frontend hot reload

```bash
cd frontend && npm install && npm run dev
# Reloads on file changes, port 3000
```

### Backend hot reload

```bash
# Stop the Docker backend
docker compose stop backend

# Run locally instead
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Still connects to Docker postgres/valkey/minio
```

### ML service hot reload

You would do this on the remote server:

```bash
ssh user@remote-server
cd lipi/ml
pip install -r requirements.txt
python main.py --reload
```

The local SSH tunnel will automatically connect to the reloaded service.

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
