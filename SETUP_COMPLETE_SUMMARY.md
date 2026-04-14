# ✅ LIPI Remote Server Setup — COMPLETE

**Date:** April 14, 2026  
**Status:** Ready for hybrid development

---

## What's Been Done ✓

### Remote Server (`202.51.2.50:41447` / `/data/lipi`)

- ✅ **Code copied** — All LIPI source code synced to `/data/lipi`
  - `backend/` — FastAPI application code
  - `frontend/` — Next.js 14 PWA application
  - `ml/` — STT/TTS microservice code
  - `scripts/`, `monitoring/`, `Makefile` — Operations tools

- ✅ **Configuration created** — `.env` file with all credentials
  - PostgreSQL: `lipi` / `lipi_secure_password_change_me_in_prod`
  - MinIO: `lipiuser` / `lipipassword_change_me`
  - JWT/Auth secrets generated and stored
  - vLLM configured with `Qwen/Qwen2.5-32B-Instruct-GGUF`

- ✅ **Docker Compose ready** — `docker-compose.yml` configured for all services
  - PostgreSQL 16 + pgvector
  - Valkey (Redis fork) for caching
  - MinIO for object storage
  - vLLM for LLM inference
  - ML service for STT/TTS
  - Backend FastAPI application

- ✅ **Backend Docker image built** — Ready to run
  - Image: `lipi-backend:latest` (673MB)
  - Fully configured with all dependencies

- ✅ **Database schema** — `init-db.sql` in place for initialization

---

## Your Development Options

### Option 1: Run Backend Locally (Recommended for fast iteration)

**Best for:** Rapid code changes, hot-reload development

```bash
# Terminal 1: SSH Tunnel (keep open)
ssh -p 41447 -L 8000:localhost:8000 -L 8080:localhost:8080 -L 5001:localhost:5001 -L 5432:localhost:5432 -L 6379:localhost:6379 ekduiteen@202.51.2.50

# Terminal 2: Backend (local Python)
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://lipi:lipi_secure_password_change_me_in_prod@localhost:5432/lipi
export VLLM_URL=http://localhost:8080
export VALKEY_URL=valkey://localhost:6379/0
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=lipiuser
export MINIO_SECRET_KEY=lipipassword_change_me
export JWT_SECRET=fab2865c45f73e8a546747c7563f897d94c0a3675a4c061da0d760d158699ba7
uvicorn main:app --reload --port 8000

# Terminal 3: Frontend (local Node)
cd frontend
export NEXT_PUBLIC_API_URL=http://localhost:8000
npm install && npm run dev
```

**Result:** Both backend and frontend auto-reload when you save code. Perfect for development.

---

### Option 2: Run Backend in Docker (Recommended for stable setup)

**Best for:** Matching production environment, stable testing

```bash
# Terminal 1: SSH Tunnel (keep open)
ssh -p 41447 ekduiteen@202.51.2.50

# Terminal 2: Inside SSH session
cd /data/lipi
docker compose up -d backend postgres valkey minio vllm ml

# Terminal 3: Local frontend (still)
cd frontend
export NEXT_PUBLIC_API_URL=http://localhost:8000
npm install && npm run dev
```

**SSH Tunnel needed to forward ports from remote to local.**

---

## Quick Start (Recommended Path)

1. **Copy** the SSH tunnel command to your terminal
2. **Keep it running** — this is your connection to the server
3. **In another terminal**, follow the "Option 1" steps above to run backend locally
4. **In a third terminal**, run frontend locally
5. **Open** http://localhost:3000 in your browser
6. **Start coding** — changes auto-reload in 1-3 seconds

---

## Files You Need

### Quick Reference
- **[SETUP_QUICK_REFERENCE.txt](SETUP_QUICK_REFERENCE.txt)** — Copy/paste commands
- **[HYBRID_DEV_SETUP_FINAL.md](HYBRID_DEV_SETUP_FINAL.md)** — Full setup guide

### Remote Server
```
/data/lipi/.env                      ← All credentials & config
/data/lipi/docker-compose.yml        ← Service definitions
/data/lipi/backend/                  ← FastAPI code
/data/lipi/frontend/                 ← Next.js code
/data/lipi/ml/                       ← STT/TTS code
```

### What's Configured
```
Database:     PostgreSQL 16 (localhost:5432 via tunnel)
Cache:        Valkey (localhost:6379 via tunnel)
Storage:      MinIO (localhost:9000 via tunnel)
LLM:          vLLM with Qwen (localhost:8080 via tunnel)
ML Services:  STT/TTS (localhost:5001 via tunnel)
Backend:      FastAPI (localhost:8000 local or via tunnel)
Frontend:     Next.js (localhost:3000 local)
```

---

## Test Your Setup

Once everything is running, test in a fourth terminal:

```bash
# Backend health
curl http://localhost:8000/health | jq

# vLLM available
curl http://localhost:8080/v1/models | jq

# Database connected
psql -h localhost -p 5432 -U lipi -d lipi -c "SELECT version();"

# Frontend
open http://localhost:3000
```

All should return valid responses.

---

## Next Steps

1. ✅ **Read** [SETUP_QUICK_REFERENCE.txt](SETUP_QUICK_REFERENCE.txt)
2. ✅ **Open 3 terminals** on your local machine
3. ✅ **Run the SSH tunnel** in Terminal 1 (keep it open)
4. ✅ **Run the backend** in Terminal 2 (local or docker)
5. ✅ **Run the frontend** in Terminal 3
6. ✅ **Open** http://localhost:3000 in your browser
7. ✅ **Start coding!**

---

## Credentials Reference

### Remote Access
```
Host:     202.51.2.50
Port:     41447
User:     ekduiteen
Path:     /data/lipi
```

### Database
```
User:       lipi
Password:   lipi_secure_password_change_me_in_prod
Database:   lipi
Port:       5432 (via SSH tunnel)
```

### Object Storage (MinIO)
```
Access Key:  lipiuser
Secret Key:  lipipassword_change_me
URL:         localhost:9000 (via SSH tunnel)
Console:     localhost:9001 (via SSH tunnel)
```

### Authentication
```
JWT Secret:       fab2865c45f73e8a546747c7563f897d94c0a3675a4c061da0d760d158699ba7
NEXTAUTH Secret:  d8b632f9267d5b115cb1d7c9e5682947c2151ae1744fa20f640b0d1aff3cda8b
```

### LLM Inference
```
vLLM URL:    http://localhost:8080
Model:       Qwen/Qwen2.5-32B-Instruct-GGUF
ML Service:  http://localhost:5001
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ YOUR LOCAL MACHINE                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Terminal 1: SSH Tunnel (8000, 8080, 5001, 5432, 6379, 9000)   │
│ Terminal 2: Backend (localhost:8000) + uvicorn --reload        │
│ Terminal 3: Frontend (localhost:3000) + npm run dev             │
│                                                                  │
│           ↓ HTTPS SSH Tunnel ↓                                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ REMOTE SERVER (202.51.2.50:41447)                               │
├─────────────────────────────────────────────────────────────────┤
│ /data/lipi                                                      │
│  ├─ PostgreSQL 16 (5432)                                        │
│  ├─ Valkey (6379)                                               │
│  ├─ MinIO (9000)                                                │
│  ├─ vLLM Qwen (8080)                                            │
│  ├─ ML Service (5001)                                           │
│  └─ (Optional) Backend in Docker                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Development Workflow

```
1. Modify code locally (backend or frontend)
2. Save file
3. Auto-reload triggers (1-3 seconds)
4. Test in browser or via API
5. Repeat
```

All requests tunnel through SSH to access remote GPU and services.

---

## Troubleshooting Quick Links

**Problem:** Can't connect to database
- **Fix:** Verify SSH tunnel is running with `-L 5432:localhost:5432`
- **Test:** `psql -h localhost -p 5432 -U lipi -d lipi`

**Problem:** vLLM not responding
- **Fix:** Model is loading (5-10 min first time), check with `curl http://localhost:8080/v1/models`
- **Remote logs:** `docker compose logs -f vllm`

**Problem:** Frontend can't reach backend
- **Fix:** Check backend is running on 8000, verify `NEXT_PUBLIC_API_URL=http://localhost:8000`
- **Test:** `curl http://localhost:8000/health`

**Problem:** SSH tunnel closed
- **Fix:** Reconnect: `ssh -p 41447 -L ...`
- **Note:** Keep a note of this command, you'll use it every session

---

## You're All Set! 🚀

Everything is configured and ready. Follow the quick reference guide and you'll be coding within 5 minutes.

**Questions?** Check:
- [HYBRID_DEV_SETUP_FINAL.md](HYBRID_DEV_SETUP_FINAL.md) — Full setup guide
- [SETUP_QUICK_REFERENCE.txt](SETUP_QUICK_REFERENCE.txt) — Commands & credentials
- `/data/lipi/.env` — All configuration on remote server

---

**Happy coding!** 🎉
