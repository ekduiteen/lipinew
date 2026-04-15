# LIPI Local Development — Status & Architecture

**Date:** 2026-04-15  
**Status:** ✅ All local services running, remote GPU services connected via SSH tunnel

---

## Architecture Confirmed

### Local Machine (CPU-only)
```
Frontend: npm run dev → localhost:3000 ✅
Backend:  Docker → localhost:8000 ✅  
DB:       Docker postgres → localhost:5432 ✅
Cache:    Docker valkey → localhost:6379 ✅
Storage:  Docker minio → localhost:9000 ✅
```

### Remote GPU Server (202.51.2.50:41447)
```
vLLM:     port 8100 (Qwen2.5-14B-AWQ) ✅
ML:       port 5001 (STT + TTS) ✅
```

### SSH Tunnel (localhost port forwarding)
```bash
ssh -p 41447 -L 8100:localhost:8100 -L 5001:localhost:5001 ekduiteen@202.51.2.50
```
Status: ✅ **Active**
- vLLM accessible at: http://localhost:8100 ✅
- ML service accessible at: http://localhost:5001 ✅

---

## Service Status

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| Frontend (Next.js) | 3000 | ✅ Running | `npm run dev` |
| Backend (FastAPI) | 8000 | ✅ Running | Docker container |
| PostgreSQL | 5432 | ✅ Running | Docker container |
| Valkey | 6379 | ✅ Running | Docker container |
| MinIO | 9000 | ✅ Running | Docker container |
| vLLM (remote) | 8100 | ✅ Connected | Via SSH tunnel |
| ML (remote) | 5001 | ✅ Connected | Via SSH tunnel |

---

## Docker Compose Configuration

Updated to reflect local-only services:
- ✅ Commented out `frontend` (runs via npm locally instead)
- ✅ Commented out `vllm` (runs on remote server)
- ✅ Commented out `ml` (runs on remote server)
- ✅ Commented out `caddy` (production only)
- ✅ Kept `backend`, `postgres`, `valkey`, `minio` for local dev

Running: `docker compose up -d postgres valkey minio minio-init backend`

---

## Testing the Full Flow

### From your local machine:

1. **Frontend:** Open http://localhost:3000
   - See landing page with Nepali/English bilingual text
   - Two buttons: "Continue with Google" + "Demo Login (dev only)"

2. **Demo login:** Click "Demo Login (dev only)"
   - Frontend → `POST /api/auth/demo` (via Next.js proxy)
   - Backend receives request through Docker network
   - Returns JWT token

3. **Onboarding:** Complete 7-question flow
   - Frontend sends data → Backend saves to postgres
   - Backend caches profile in Valkey

4. **Teach session:** Click to start conversation
   - Frontend opens WebSocket to `/ws/session/{id}`
   - Audio → VAD → STT (via SSH tunnel to port 5001)
   - STT output → vLLM (via SSH tunnel to port 8100)
   - LLM output → TTS (via SSH tunnel to port 5001)
   - TTS audio → Frontend plays back

All API calls go through the Next.js proxy route (no CORS issues).

---

## To Keep Everything Running

### Terminal 1 — SSH Tunnel (keep active)
```bash
ssh -p 41447 -L 8100:localhost:8100 -L 5001:localhost:5001 ekduiteen@202.51.2.50
```
Keep this running for the duration of development.

### Terminal 2 — Frontend
```bash
cd frontend && npm run dev
```
Listens on http://localhost:3000 with hot reload.

### Terminal 3 — Backend infrastructure (one-time)
```bash
docker compose up -d postgres valkey minio minio-init backend
```
All services stay running in background.

---

## Key Environment Variables

Backend sees these from `.env`:
```
VLLM_URL=http://localhost:8100        # via SSH tunnel
ML_SERVICE_URL=http://localhost:5001  # via SSH tunnel
DATABASE_URL=postgresql+asyncpg://lipi:password@postgres:5432/lipi
VALKEY_URL=valkey://valkey:6379/0
```

Frontend gets `.env.local`:
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## Common Commands

```bash
# Check if tunnel is working
curl http://localhost:8100/v1/models
curl http://localhost:5001/health

# View backend logs
docker compose logs backend -f

# Stop everything
docker compose down

# Start fresh
docker compose up -d postgres valkey minio minio-init backend
cd frontend && npm run dev
```

---

## Next Steps

1. ✅ Architecture corrected (GPU services on remote, frontend local)
2. ✅ SSH tunnel established
3. ✅ All services verified healthy
4. **→ Test the full conversation flow through the UI**
5. → Monitor for any issues in fallback chains (Groq STT/LLM)
6. → Collect stability metrics for production readiness report

---

**This setup is correct.** Do not run vLLM or ML services locally. SSH tunnel handles all remote connectivity.
