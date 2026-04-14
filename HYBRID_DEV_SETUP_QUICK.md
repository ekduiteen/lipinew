# LIPI Hybrid Dev Setup — Quick Start (Using Existing qwen2.5-awq)

**30-minute setup using your existing infrastructure.**

---

## ✅ What You Already Have

```
Remote Server (1× L40S):
  ✅ vLLM on port 8100 (qwen2.5-awq, 14GB GPU, quantized)
  ✅ ML Service on port 8442 (remote-model-api)
  ✅ PostgreSQL on port 5433
  ✅ Redis/Valkey on port 6380
  ✅ MinIO on ports 9000-9001
```

**No additional downloads needed. Use what's running NOW.**

---

## 🎯 Architecture (30 minutes to run)

```
Your Local Machine
  ├─ Frontend: Next.js dev (localhost:3000)
  └─ Backend: FastAPI (localhost:8000)
       ↓ SSH tunnel
Remote Server
  ├─ vLLM: qwen2.5-awq (port 8100) ✅ ALREADY RUNNING
  ├─ ML Service: (port 8442) ✅ ALREADY RUNNING
  └─ Infra: PostgreSQL, Valkey, MinIO ✅ ALREADY RUNNING
```

---

## 🚀 Setup (4 Simple Steps)

### Step 1: SSH Tunnel (5 min)

```bash
# On your local machine, open a terminal and keep it running:
ssh -p 41447 -L 8100:localhost:8100 \
    -L 5001:localhost:5001 \
    -L 5434:localhost:5434 \
    -L 6380:localhost:6380 \
    -L 9000:localhost:9000 \
    ekduiteen@202.51.2.50

# Port mapping:
# 8100 → vLLM (qwen2.5-awq)
# 5001 → ML Service (will mock/fallback locally)
# 5434 → PostgreSQL
# 6380 → Valkey cache
# 9000 → MinIO
```

### Step 2: Create `.env.local` (5 min)

```bash
# In your local /path/to/lipi folder
cat > .env.local << 'EOF'
# Backend → Remote GPU services
VLLM_URL=http://localhost:8100
ML_SERVICE_URL=http://localhost:5001
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5434/lipi
VALKEY_URL=valkey://localhost:6380/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=lipi_minio_admin
MINIO_SECRET_KEY=minioadmin

# Frontend → Local backend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id
NEXT_PUBLIC_GOOGLE_CLIENT_SECRET=your_google_client_secret

# App config
ENVIRONMENT=development
LOG_LEVEL=DEBUG
JWT_SECRET=dev-secret-change-in-prod
NEXTAUTH_SECRET=dev-secret-change-in-prod
EOF
```

### Step 3: Start Backend (5 min)

```bash
cd backend
pip install -r requirements.txt

# Set env vars
export VLLM_URL=http://localhost:8100
export ML_SERVICE_URL=http://localhost:5001
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5434/lipi
export VALKEY_URL=valkey://localhost:6380/0

# Run with hot-reload
uvicorn main:app --reload --port 8000

# Output should show:
# Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### Step 4: Start Frontend (5 min)

```bash
# New terminal
cd frontend
npm install  # only if not done
npm run dev

# Should show:
# ▲ Next.js 14.x.x
# - Local: http://localhost:3000
```

---

## ✅ Verify Everything Works

```bash
# Terminal 1: Check vLLM is accessible
curl http://localhost:8100/v1/models | jq

# Terminal 2: Check backend health
curl http://localhost:8000/health | jq

# Browser: Visit http://localhost:3000
# Should see landing page (लिपि)
```

---

## 🔄 Development Workflow

```
You change code locally
  ↓
Backend auto-reloads (uvicorn --reload)
Frontend auto-reloads (Next.js dev server)
  ↓
Test in http://localhost:3000
  ↓
All requests → local backend → remote vLLM (qwen2.5-awq)
  ↓
Loop: change code, test, repeat
```

---

## ⚡ Performance (with qwen2.5-awq)

| Metric | Expected | Notes |
|--------|----------|-------|
| LLM inference | 2-4s | qwen2.5-awq is quantized, slightly slower than fp16 |
| STT latency | ~200ms | ML service fallback (CPU if needed) |
| TTS latency | ~500ms | CPU if needed |
| End-to-end | 3-6s | Acceptable for dev |
| Concurrent users | 1-2 | Perfect for local testing |

**Good for:** Development, code iteration, testing prompts  
**Not ideal for:** Load testing (upgrade to Qwen3-32B later)

---

## 📊 qwen2.5-awq vs Qwen3-32B

| Aspect | qwen2.5-awq | Qwen3-32B | Use Now? |
|--------|------------|-----------|----------|
| Nepali support | Good (201 languages) | Excellent (201 languages) | ✅ Yes, good enough |
| Quality | 85% (quantized) | 100% (full precision) | ✅ Fine for dev |
| Speed | Faster | Slightly slower | ✅ Better for dev |
| VRAM | ~14GB | ~32GB | ✅ More headroom |
| Download time | 0 (already running) | 25GB (~20 min) | ✅ Save time |
| Latency | 2-4s | 3-6s (slower) | ✅ Faster actually! |

**Verdict: qwen2.5-awq is PERFECT for development right now.** Upgrade to Qwen3-32B when you need production-grade quality.

---

## 🔄 Upgrade Path (Later, when ready)

When you want to upgrade to Qwen3-32B:

```bash
# On remote server
ssh -p 41447 ekduiteen@202.51.2.50

# Download Qwen3-32B (~25GB)
python3 << 'PYTHON'
from huggingface_hub import snapshot_download
snapshot_download(
    "Qwen/Qwen3-32B",
    cache_dir="/data/cache/huggingface",
    local_dir="/data/models/qwen3-32b",
    resume_download=True
)
PYTHON

# Update docker-compose.yml to use Qwen3-32B instead
# Restart vLLM service
# Done!
```

**No changes to local dev needed.** Just restart the remote vLLM service.

---

## 📋 Quick Checklist

- [ ] SSH tunnel running: `ssh -p 41447 -L ...`
- [ ] `.env.local` created with correct values
- [ ] Backend running: `uvicorn main:app --reload`
- [ ] Frontend running: `npm run dev`
- [ ] http://localhost:3000 loads landing page
- [ ] http://localhost:8000/health returns OK
- [ ] http://localhost:8100/v1/models returns models list

---

## 🎯 Database Note

Your existing PostgreSQL (port 5433/5434):
- Check if it already has LIPI schema
- If not, run: `docker compose exec postgres psql -U lipi -d lipi < init-db.sql`
- Or manually run the schema from `init-db.sql`

---

## 🆘 Troubleshooting

**Backend can't reach vLLM:**
```bash
# Check SSH tunnel is running
# Check port 8100 is forwarded
curl http://localhost:8100/v1/models
```

**Frontend can't reach backend:**
```bash
# Check backend is running on 8000
curl http://localhost:8000/health
```

**Database connection error:**
```bash
# Check port 5434 is forwarded
psql -h localhost -p 5434 -U lipi -d lipi
```

**GPU too slow:**
- This is qwen2.5-awq being quantized. It's still reasonably fast.
- If you need faster inference, upgrade to Qwen3-32B later.

---

## ⏱️ Total Setup Time

- SSH tunnel: 1 min
- `.env.local`: 1 min  
- Backend setup: 3 min
- Frontend setup: 3 min
- Verification: 2 min
- **Total: ~10 minutes**

Compare to 50-60 min if downloading Qwen3-32B! 🚀

---

## 🎉 You're Ready!

No model downloads. No waiting. Just code.

**Next:** Open http://localhost:3000 and start developing LIPI!

---

## Later: Upgrade to Qwen3-32B

When you're ready for production quality (in a few weeks):

1. Download Qwen3-32B on remote server (~25GB, ~20 min)
2. Update vLLM to serve Qwen3-32B
3. Restart remote vLLM (~5 min)
4. No code changes needed — everything still works

That's it! 🚀

---

**Let me know if you hit any issues!**
