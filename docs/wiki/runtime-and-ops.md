# Runtime And Ops

## Local Ports

| Service | Port |
|---|---|
| public frontend | `3000` |
| control dashboard | `3001` |
| backend | `8000` |
| ML service | `5001` when local/tunneled |
| Postgres | `5432` |
| Valkey | `6379` |
| MinIO API | `9000` |
| MinIO console | `9001` |
| Prometheus | `9090` |

## Main Commands

Root Makefile:

- `make dev`: start local infra/backend stack.
- `make prod`: start production stack.
- `make monitoring`: start monitoring profile.
- `make down`: stop containers.
- `make logs`: follow compose logs.
- `make health`: show container and backend health.
- `make build`: rebuild backend/frontend/ml images.
- `make db-shell`: open psql.
- `make valkey-shell`: open valkey-cli.

Frontend apps:

- `cd frontend && npm run dev`
- `cd frontend && npm run build`
- `cd frontend-control && npm run dev`
- `cd frontend-control && npm run build`

Backend tests:

- `cd backend && pytest`

## Environment Clusters

Important env groups:

- app/origin: `APP_URL`, `NEXTAUTH_URL`, `NEXT_PUBLIC_*`
- database: `DATABASE_URL`, `POSTGRES_*`
- Valkey: `VALKEY_URL`
- object storage: `MINIO_*`
- model: `VLLM_URL`, `VLLM_MODEL`, `VLLM_TIMEOUT`
- ML: `ML_SERVICE_URL`, `STT_TIMEOUT`, `TTS_TIMEOUT`
- auth: `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_HOURS`, Google client vars
- speech: `STT_DEVICE`, `TTS_DEVICE`, `TTS_PROVIDER`, Piper/XTTS vars
- intelligence toggles: intent/entity/keyterm/repair thresholds

`JWT_SECRET` must be 32+ chars and cannot be a default value.

## Health Checks

Backend:

- `GET http://localhost:8000/health`

ML:

- `GET http://localhost:5001/health`
- `GET http://localhost:5001/models/info`

Control:

- admin `/api/ctrl/system/health`

Infrastructure:

- `docker compose ps`
- Postgres `pg_isready`
- Valkey `PING`
- MinIO live health

## Remote/Hybrid Notes

Existing docs describe a remote NVIDIA L40S setup. Local dev often uses:

- local frontend/backend/DB/cache/storage
- remote/tunneled ML and model endpoints

Current ops guidance from root docs:

- commit backend changes before remote deploy
- sync committed source to `/data/lipi`
- rebuild remote backend image
- verify backend `/health`, ML `/health`, and model `/v1/models`
- avoid assuming remote host is a clean git checkout

## Common Breaks

| Problem | Check |
|---|---|
| Frontend cannot call backend | `BACKEND_URL`, `NEXT_PUBLIC_API_URL`, proxy routes |
| WebSocket fails | `NEXT_PUBLIC_WS_URL`, `/auth/ws-token`, backend CORS/origin |
| Backend startup fails | `JWT_SECRET`, DB migration, Valkey, env file mount |
| STT/TTS unavailable | `ML_SERVICE_URL`, ML `/health`, GPU/provider startup |
| Model call fails | `VLLM_URL`, model name, remote tunnel, fallback config |
| Control dashboard blank/failing | `BACKEND_URL` or `NEXT_PUBLIC_API_URL`, admin auth cookie |

