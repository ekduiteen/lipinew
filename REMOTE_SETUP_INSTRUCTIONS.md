# LIPI Remote Server Setup — Complete Instructions

**Status:** `.env` and `docker-compose.override.yml` created at `/data/lipi/` on remote server  
**Next:** Copy LIPI code files to remote server

---

## ✅ What's Already Done on Remote Server

```
/data/lipi/
├── .env                          ✅ Created (configured for hybrid dev)
└── docker-compose.override.yml   ✅ Created (uses existing services)
```

---

## 📋 Remaining: Copy Code Files to Remote

**From your LOCAL machine** (where you have the LIPI repo):

```bash
# Copy these directories from local /path/to/lipi/ to remote /data/lipi/

# 1. Backend code
scp -P 41447 -r backend ekduiteen@202.51.2.50:/data/lipi/

# 2. Frontend code  
scp -P 41447 -r frontend ekduiteen@202.51.2.50:/data/lipi/

# 3. ML service code
scp -P 41447 -r ml ekduiteen@202.51.2.50:/data/lipi/

# 4. Main configuration files
scp -P 41447 docker-compose.yml ekduiteen@202.51.2.50:/data/lipi/
scp -P 41447 Caddyfile ekduiteen@202.51.2.50:/data/lipi/
scp -P 41447 init-db.sql ekduiteen@202.51.2.50:/data/lipi/

# 5. Scripts and monitoring
scp -P 41447 -r scripts ekduiteen@202.51.2.50:/data/lipi/
scp -P 41447 -r monitoring ekduiteen@202.51.2.50:/data/lipi/

# 6. Configuration files
scp -P 41447 Makefile ekduiteen@202.51.2.50:/data/lipi/ || true
```

**Or all at once:**

```bash
# From /path/to/lipi directory:
scp -P 41447 -r backend frontend ml docker-compose.yml Caddyfile init-db.sql scripts monitoring Makefile ekduiteen@202.51.2.50:/data/lipi/ 2>&1 | tail -10
```

---

## 🔧 After Files Are Copied (On Remote Server)

```bash
ssh -p 41447 ekduiteen@202.51.2.50

cd /data/lipi

# Verify structure
ls -la

# Should show:
# ├── .env
# ├── docker-compose.yml
# ├── docker-compose.override.yml
# ├── Caddyfile
# ├── backend/
# ├── frontend/
# ├── ml/
# ├── scripts/
# ├── monitoring/
# └── init-db.sql
```

---

## 🚀 Start LIPI Services (On Remote Server)

Once files are copied:

```bash
ssh -p 41447 ekduiteen@202.51.2.50

cd /data/lipi

# Start only LIPI services (reuse existing postgres, valkey, minio)
docker compose up -d backend frontend

# Monitor startup
docker compose logs -f backend

# Should see:
# backend_1 | INFO:     Uvicorn running on http://0.0.0.0:8000
# frontend_1 | ▲ Next.js 14.x.x
```

---

## 💻 Setup Local Dev Machine (Your Computer)

### Terminal 1: SSH Tunnel

```bash
ssh -p 41447 -L 8000:localhost:8000 \
    -L 3000:localhost:3000 \
    -L 8100:localhost:8100 \
    -L 5001:localhost:5001 \
    -L 5434:localhost:5434 \
    -L 6380:localhost:6380 \
    -L 9000:localhost:9000 \
    ekduiteen@202.51.2.50

# Keep this running. You should see:
# ekduiteen@remote-server:~$
```

### Terminal 2: Open Browser

```bash
# Frontend (Next.js running on remote)
open http://localhost:3000

# Backend health check
curl http://localhost:8000/health | jq
```

---

## 🎯 Final Architecture

```
Your Local Machine
  ├─ Browser → http://localhost:3000
  │            (Next.js from remote, served via SSH tunnel)
  └─ Terminal: SSH tunnel keeping ports open

Remote Server (/data/lipi)
  ├─ Frontend (Next.js on 3000)
  ├─ Backend (FastAPI on 8000)
  ├─ vLLM (qwen2.5-awq on 8100) ← existing
  ├─ ML Service (on 5001) ← existing
  ├─ PostgreSQL (on 5434) ← existing
  ├─ Valkey (on 6380) ← existing
  └─ MinIO (on 9000) ← existing
```

---

## ✅ Verification Checklist

- [ ] All code files copied to `/data/lipi/`
- [ ] `.env` file exists at `/data/lipi/.env`
- [ ] `docker-compose.override.yml` exists
- [ ] `docker compose up -d backend frontend` succeeds
- [ ] `docker compose logs backend` shows no errors
- [ ] SSH tunnel is running on local machine
- [ ] `curl http://localhost:8000/health` returns OK
- [ ] `open http://localhost:3000` loads landing page
- [ ] "लिपि" title visible on landing page

---

## 🔄 Development Workflow

```
You change code locally? 
→ Need to push changes to remote
→ Copy changed files via scp
→ Remote auto-reloads (if uvicorn --reload is on)
→ OR manually restart: docker compose restart backend/frontend
```

**For faster dev iteration**, consider:
- Running backend locally too (connect to remote DB/vLLM only)
- Using git + CI/CD to auto-deploy changes

---

## 📞 Next Steps

1. **Copy files to remote** (see SCP commands above)
2. **Start services on remote** (docker compose up -d)
3. **SSH tunnel from local** (keep running)
4. **Visit http://localhost:3000** (should see LIPI)
5. **Start coding!**

---

## 🆘 Troubleshooting

**Files copied but services won't start:**
```bash
ssh -p 41447 ekduiteen@202.51.2.50
cd /data/lipi
docker compose up -d backend frontend
docker compose logs backend  # Check errors
```

**Can't access from localhost:3000:**
```bash
# Check SSH tunnel is running
# Check: ssh -L 3000:localhost:3000 is in the tunnel
netstat -tlnp | grep 3000  # Should show LISTEN
```

**Backend can't reach vLLM:**
```bash
# Check vLLM is still running
ssh -p 41447 ekduiteen@202.51.2.50
curl http://localhost:8100/v1/models | jq  # Should return models
```

---

## 📊 Configuration Summary

| Service | Port | Location | Status |
|---------|------|----------|--------|
| Frontend | 3000 | Remote, via SSH tunnel | New ✅ |
| Backend | 8000 | Remote, via SSH tunnel | New ✅ |
| vLLM | 8100 | Remote (localhost) | Existing ✅ |
| ML Service | 5001 | Remote (localhost) | Existing ✅ |
| PostgreSQL | 5434 | Remote Docker | Existing ✅ |
| Valkey | 6380 | Remote Docker | Existing ✅ |
| MinIO | 9000 | Remote Docker | Existing ✅ |

**All routed via SSH tunneling to your local machine for development.**

---

## 🎉 You're Almost Done!

Just copy the code files (5 min), start the services (2 min), and you're ready to code!
