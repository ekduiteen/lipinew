# LIPI Hybrid Development Setup — Ready to Go

Your remote server is configured and ready. Here's how to develop locally with remote GPU access.

---

## ✅ Remote Server Status

**Location:** `/data/lipi` on `202.51.2.50:41447`

**Services Ready:**
- ✅ PostgreSQL (port 5432)
- ✅ Valkey/Redis (port 6379)
- ✅ MinIO object storage (port 9000)
- ✅ vLLM with Qwen model (port 8080)
- ✅ ML service STT/TTS (port 5001)
- ✅ Backend FastAPI container (port 8000)

**Configuration:**
- Database: `lipi`
- Credentials: See `/data/lipi/.env`

---

## 🚀 Local Development Setup (Your Machine)

### Step 1: SSH Tunnel (Keep Running)

Open a terminal and establish an SSH tunnel to access remote services:

```bash
ssh -p 41447 \
  -L 8000:localhost:8000 \
  -L 8080:localhost:8080 \
  -L 5001:localhost:5001 \
  -L 5432:localhost:5432 \
  -L 6379:localhost:6379 \
  -L 9000:localhost:9000 \
  ekduiteen@202.51.2.50
```

**Keep this terminal open while developing.** You should see:
```
ekduiteen@remote-server:~$
```

---

### Step 2: Local Backend (Development)

In a new terminal, run the FastAPI backend locally:

```bash
cd /path/to/lipi/backend

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://lipi:lipi_secure_password_change_me_in_prod@localhost:5432/lipi"
export VALKEY_URL="valkey://localhost:6379/0"
export VLLM_URL="http://localhost:8080"
export ML_SERVICE_URL="http://localhost:5001"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="lipiuser"
export MINIO_SECRET_KEY="lipipassword_change_me"
export JWT_SECRET="fab2865c45f73e8a546747c7563f897d94c0a3675a4c061da0d760d158699ba7"
export GOOGLE_CLIENT_ID="your_google_client_id"
export GOOGLE_CLIENT_SECRET="your_google_client_secret"
export LOG_LEVEL="DEBUG"

# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --reload --port 8000 --host 0.0.0.0
```

**Output should show:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

---

### Step 3: Local Frontend (Development)

In another terminal:

```bash
cd /path/to/lipi/frontend

# Set environment variables
export NEXT_PUBLIC_API_URL="http://localhost:8000"
export NEXT_PUBLIC_WS_URL="ws://localhost:8000"

# Install dependencies
npm install

# Run dev server
npm run dev
```

**Output should show:**
```
▲ Next.js 14.x.x
- Local: http://localhost:3000
```

---

## 📍 Test Everything Works

Once all three pieces are running (SSH tunnel, backend, frontend):

```bash
# Test backend health (from your local machine)
curl http://localhost:8000/health | jq

# Test vLLM access
curl http://localhost:8080/v1/models | jq

# Open frontend
open http://localhost:3000
```

**You should see:**
- Backend health check returns OK
- vLLM shows available models
- Landing page loads with "लिपि" title

---

## 🔧 Environment Variables Explained

**From `/data/lipi/.env` on remote:**
```bash
POSTGRES_PASSWORD=lipi_secure_password_change_me_in_prod
MINIO_ACCESS_KEY=lipiuser
MINIO_SECRET_KEY=lipipassword_change_me
JWT_SECRET=fab2865c45f73e8a546747c7563f897d94c0a3675a4c061da0d760d158699ba7
VLLM_MODEL_NAME=Qwen/Qwen2.5-32B-Instruct-GGUF
TENSOR_PARALLEL_SIZE=1
```

**Use these same values when running backend locally** (copy/paste above).

---

## 💡 Development Workflow

```
1. Modify backend code locally → saved to disk
2. Uvicorn auto-reloads → takes 1-2 seconds
3. Test via curl or frontend
4. Modify frontend code → saved
5. Next.js auto-reloads → takes 2-3 seconds
6. Refresh browser → see changes
7. Repeat
```

**All requests from your local machine go through the SSH tunnel to access remote services.**

---

## 🆘 Troubleshooting

**Backend can't connect to database:**
```bash
# Check PostgreSQL is accessible
psql -h localhost -p 5432 -U lipi -d lipi
# If this works, database is reachable

# Make sure SSH tunnel is active (step 1)
```

**Frontend can't reach backend:**
```bash
# Check backend is running on port 8000
curl http://localhost:8000/health

# Check NEXT_PUBLIC_API_URL is set correctly
echo $NEXT_PUBLIC_API_URL  # should be http://localhost:8000
```

**vLLM not responding:**
```bash
# Check it's available via tunnel
curl http://localhost:8080/v1/models | jq

# If timeout, the model is still loading (5-10 min on first start)
```

**Port already in use:**
```bash
# Kill the process
lsof -i :8000  # find process on port 8000
kill -9 <PID>  # kill it
```

---

## 🎯 What You Have

- **Remote:** All GPU services, databases, caching, object storage
- **Local:** Fast, iterative development with hot-reload
- **Connection:** SSH tunnel keeps everything connected

**Perfect for:** Rapid prototyping, testing, debugging

---

## 📊 Architecture Overview

```
Your Local Machine
  ├─ Terminal 1: SSH Tunnel (keeps connection open)
  ├─ Terminal 2: Backend (uvicorn --reload on :8000)
  └─ Terminal 3: Frontend (npm run dev on :3000)
       ↓ SSH Tunnel
       ↓
Remote Server (202.51.2.50:41447)
  ├─ PostgreSQL (5432)
  ├─ Valkey (6379)
  ├─ MinIO (9000)
  ├─ vLLM Qwen (8080)
  └─ ML Service (5001)
```

---

## ✨ Next Steps

1. ✅ Open 3 terminals on your local machine
2. ✅ Terminal 1: Run the SSH tunnel command
3. ✅ Terminal 2: Run the backend
4. ✅ Terminal 3: Run the frontend
5. ✅ Open http://localhost:3000 in browser
6. ✅ Start coding!

---

**You're all set. Happy coding!** 🚀
