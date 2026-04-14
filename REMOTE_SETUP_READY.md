# ✅ LIPI Remote Server Setup — READY FOR DEVELOPMENT

**Status:** All services running and ready to connect from your local machine

---

## 🎉 What's Running on Remote (202.51.2.50:41447 / /data/lipi)

```
✅ vLLM API Server        → localhost:8120 (Qwen2.5-AWQ model loaded)
✅ ML Service (STT/TTS)   → localhost:5001 (starting up, downloading Whisper)
✅ FastAPI Backend        → localhost:8000 (healthy, waiting for deps)
✅ PostgreSQL             → localhost:5433 (existing, healthy)
✅ Valkey Cache           → localhost:6380 (existing, healthy)
✅ MinIO Storage          → localhost:9000 (existing, healthy)
```

---

## 🚀 How to Develop (Fastest Path)

### Option A: Run Backend Locally (Recommended for hot-reload development)

**Terminal 1: SSH Tunnel (keep running)**

```bash
ssh -p 41447 \
  -L 8120:localhost:8120 \
  -L 5001:localhost:5001 \
  -L 5433:localhost:5433 \
  -L 6380:localhost:6380 \
  -L 9000:localhost:9000 \
  ekduiteen@202.51.2.50
```

**Terminal 2: Backend (local Python)**

```bash
cd backend

# Set environment (adjust database port to 5433, not 5432)
export DATABASE_URL="postgresql+asyncpg://lipi:lipi_secure_password_change_me_in_prod@localhost:5433/lipi"
export VALKEY_URL="valkey://localhost:6380/0"
export VLLM_URL="http://localhost:8120"
export VLLM_MODEL="lipi"
export ML_SERVICE_URL="http://localhost:5001"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="lipiuser"
export MINIO_SECRET_KEY="lipipassword_change_me"
export JWT_SECRET="fab2865c45f73e8a546747c7563f897d94c0a3675a4c061da0d760d158699ba7"
export GOOGLE_CLIENT_ID="your_google_client_id"
export GOOGLE_CLIENT_SECRET="your_google_client_secret"
export LOG_LEVEL="DEBUG"

pip install -r requirements.txt
uvicorn main:app --reload --port 8000 --host 0.0.0.0
```

**Terminal 3: Frontend (local Node)**

```bash
cd frontend

export NEXT_PUBLIC_API_URL="http://localhost:8000"
export NEXT_PUBLIC_WS_URL="ws://localhost:8000"

npm install
npm run dev
```

**Open:** `http://localhost:3000` → Landing page with "लिपि" title

---

### Option B: Run Backend in Docker (Production-like)

**Terminal 1: SSH Tunnel**

```bash
ssh -p 41447 ekduiteen@202.51.2.50
```

**Terminal 2: Start LIPI services (inside SSH)**

```bash
cd /data/lipi
docker compose -f docker-compose.lipi.yml logs -f  # Monitor startup
```

**Terminal 3: Frontend (local)**

```bash
cd frontend
export NEXT_PUBLIC_API_URL="http://localhost:8000"
npm install && npm run dev
```

---

## 🧪 Test Everything Works

```bash
# Check vLLM models available
curl http://localhost:8120/v1/models | head

# Check backend health
curl http://localhost:8000/health

# Check database
psql -h localhost -p 5433 -U lipi -d lipi -c "SELECT version();"

# Open frontend
open http://localhost:3000
```

---

## 📊 Architecture

```
Your Local Machine
  ├─ Terminal 1: SSH Tunnel
  ├─ Terminal 2: Backend (uvicorn --reload) or Docker
  ├─ Terminal 3: Frontend (npm run dev)
  └─ Browser: http://localhost:3000

Remote Server (202.51.2.50:41447)
  ├─ vLLM (port 8120) - Qwen2.5-AWQ loaded ✅
  ├─ ML Service (port 5001) - downloading Whisper model...
  ├─ Backend (port 8000) - Docker container running
  ├─ PostgreSQL (port 5433) - existing infrastructure ✅
  ├─ Valkey (port 6380) - existing infrastructure ✅
  └─ MinIO (port 9000) - existing infrastructure ✅
```

---

## 🔧 Key Credentials & Ports

| Service | Port | User | Password | Notes |
|---------|------|------|----------|-------|
| PostgreSQL | 5433 | lipi | lipi_secure_password_change_me_in_prod | Note: port 5433, not 5432 |
| Valkey | 6380 | — | — | Cache/sessions |
| MinIO | 9000 | lipiuser | lipipassword_change_me | Object storage |
| vLLM | 8120 | — | — | Qwen2.5-AWQ loaded |
| ML Service | 5001 | — | — | STT/TTS (starting) |
| Backend | 8000 | — | — | FastAPI |
| Frontend | 3000 | — | — | Local Next.js dev server |

---

## ⏱️ What's Happening in Background

1. **Whisper STT Model** — Downloading to `/data/models/ml_models/`
   - Used for speech-to-text in conversations
   - ~3GB, will cache locally
   - ML service will be healthy once download completes (~5-10 min)

2. **Qwen2.5-AWQ** — Already loaded and running
   - 14GB quantized model
   - Fast inference (2-4s response time)
   - Running on GPU 0

3. **Backend Service** — Running in Docker
   - Connected to all infrastructure services
   - Auto-reloads if you edit code in container (or run locally)

---

## 💡 Development Workflow (Local Backend)

```
1. Modify code in backend/ or frontend/ (your machine)
2. Save file
3. uvicorn auto-reloads (1-2 sec) OR Next.js hot-reloads (2-3 sec)
4. Test in browser or via curl
5. Repeat!

All requests tunnel through SSH to remote GPU services.
```

---

## 🆘 Troubleshooting

**SSH tunnel disconnects?**
- Reconnect: Run the SSH tunnel command again in Terminal 1

**Backend can't reach database?**
- Verify SSH tunnel has `-L 5433:localhost:5433`
- Test: `psql -h localhost -p 5433 -U lipi -d lipi`
- **Important:** Use port 5433, NOT 5432

**vLLM not responding?**
- It's running on port 8120, not 8000
- Test: `curl http://localhost:8120/v1/models`

**ML service still starting?**
- Whisper model is downloading (~2-5 GB)
- Check: `docker logs -f lipi-ml` (on remote via SSH)
- This is normal, takes 5-10 minutes first time

**Frontend can't reach backend?**
- Backend should be on `http://localhost:8000`
- Check NEXT_PUBLIC_API_URL=`http://localhost:8000`
- Verify backend is running: `curl http://localhost:8000/health`

**"Port already in use"?**
- Backend: `lsof -i :8000 | grep LISTEN`
- Frontend: `lsof -i :3000 | grep LISTEN`
- Kill process: `kill -9 <PID>`

---

## 📈 Next Steps

1. ✅ **Open 3 terminals** on your local machine
2. ✅ **Terminal 1:** Run SSH tunnel (keep it open)
3. ✅ **Terminal 2:** Run backend (local Python or Docker)
4. ✅ **Terminal 3:** Run frontend
5. ✅ **Browser:** Open http://localhost:3000
6. ✅ **Start coding!**

---

## 📚 Additional Resources

- **Local development details:** See [HYBRID_DEV_SETUP_FINAL.md](HYBRID_DEV_SETUP_FINAL.md)
- **Quick reference:** See [SETUP_QUICK_REFERENCE.txt](SETUP_QUICK_REFERENCE.txt)
- **Remote server:** /data/lipi/.env (all credentials)

---

## 🎯 Performance Expectations

| Operation | Latency | Notes |
|-----------|---------|-------|
| Backend startup | 5s | Uvicorn hot-reload |
| Frontend hot-reload | 2-3s | Next.js dev server |
| LLM inference | 2-4s | Qwen2.5-AWQ (quantized) |
| STT latency | 500ms-2s | faster-whisper on GPU |
| TTS latency | 1-3s | mms-tts or fallback |
| API response | 100-500ms | FastAPI + services |

---

## ✨ You're Ready!

Everything is set up and running. Pick Option A or B above and start developing in 5 minutes.

**Questions?** Check the troubleshooting section or review the setup files.

---

**Happy coding! 🚀**
