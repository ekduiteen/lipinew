# 🚀 LIPI — START DEVELOPING NOW

**All remote services are running and operational.**

---

## 🎯 Do This (3 Easy Steps)

### Step 1: SSH Tunnel
Open Terminal 1 and run:
```bash
ssh -p 41447 -L 8000:localhost:8000 -L 8080:localhost:8080 -L 5001:localhost:5001 -L 5432:localhost:5432 -L 6379:localhost:6379 ekduiteen@202.51.2.50
```
Keep it running. You'll see the SSH prompt.

### Step 2: Backend
Open Terminal 2:
```bash
cd backend
export DATABASE_URL="postgresql+asyncpg://lipi:lipi_secure_password_change_me_in_prod@localhost:5432/lipi"
export VALKEY_URL="valkey://localhost:6379/0"
export VLLM_URL="http://localhost:8080"
export VLLM_MODEL="lipi"
export ML_SERVICE_URL="http://localhost:5001"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="lipiuser"
export MINIO_SECRET_KEY="lipipassword_change_me"
export JWT_SECRET="fab2865c45f73e8a546747c7563f897d94c0a3675a4c061da0d760d158699ba7"
export GOOGLE_CLIENT_ID="your_id_here"
export GOOGLE_CLIENT_SECRET="your_secret_here"
export LOG_LEVEL="DEBUG"
pip install -r requirements.txt
uvicorn main:app --reload --port 8000 --host 0.0.0.0
```

### Step 3: Frontend
Open Terminal 3:
```bash
cd frontend
export NEXT_PUBLIC_API_URL="http://localhost:8000"
export NEXT_PUBLIC_WS_URL="ws://localhost:8000"
npm install
npm run dev
```

### Open Browser
```
http://localhost:3000
```

---

## ✅ What's Working on Remote

```
Remote (202.51.2.50:41447)
✅ PostgreSQL 16      (5432)
✅ Valkey             (6379)
✅ MinIO              (9000)
✅ vLLM + Qwen        (8080) ← MODEL LOADED
✅ ML Service         (5001) ← warming up
✅ FastAPI Backend    (8000)
```

---

## 🔥 That's It!

Your backend, frontend, LLM, database, cache, and storage are all connected and ready.

**Code → Save → Auto-reload → Test**

---

## 📊 What You Get

| Component | Location | Status |
|-----------|----------|--------|
| LLM | Remote GPU | ✅ Qwen2.5-AWQ (2-4s per query) |
| Database | Remote | ✅ PostgreSQL + pgvector |
| Cache | Remote | ✅ Valkey |
| Storage | Remote | ✅ MinIO |
| Backend | Local/Docker | ✅ FastAPI + hot-reload |
| Frontend | Local | ✅ Next.js + hot-reload |

---

## 🆘 Issues?

**SSH tunnel closed?** → Re-run Step 1

**Port in use?** → `lsof -i :8000` then `kill -9 <PID>`

**Backend can't reach services?** → Check SSH tunnel has all `-L` flags

**vLLM not responding?** → Port is 8080 (not 8000)

**ML service unhealthy?** → That's OK, Whisper is downloading (~5 min)

---

## 📚 Full Documentation

See [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) for details.

---

**Ready? Start the 3 terminals above and code! 🎉**
