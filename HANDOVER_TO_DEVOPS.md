# LIPI Deployment — Handover to DevOps/Operations

This document is for the DevOps engineer or operations team taking over LIPI deployment and management.

---

## 📋 Current State (as of April 14, 2026)

**LIPI is production-ready.** All code is complete and tested:
- ✅ Frontend (Next.js 14 PWA)
- ✅ Backend (FastAPI + WebSocket)
- ✅ ML services (faster-whisper STT + mms-tts-npi TTS)
- ✅ LLM inference (vLLM serving Qwen3-32B)
- ✅ Authentication (JWT + Google OAuth)
- ✅ Gamification (points, badges, leaderboards)
- ✅ Database schema (PostgreSQL + pgvector)

**Missing only:** Speaker embeddings (Phase roadmap item #1 — not blocking production launch).

---

## 🚀 Your Mission

Deploy LIPI to a remote Ubuntu 22.04 server with 2× NVIDIA L40S and make it available to teachers.

---

## 📂 Files You Need

### Start Here (in order)
1. **DEPLOYMENT_README.txt** — Quick reference card (1 page)
2. **DEPLOYMENT_QUICK_START.md** — Full 30-min setup guide
3. **DEPLOY_CHECKLIST.md** — Step-by-step checklist (printable)

### For Daily Operations
4. **OPERATIONS.md** — Admin reference (logs, backups, monitoring, recovery)

### For Understanding Architecture
5. **DEV_ONBOARDING.md** (section 6) — How a conversation turn works
6. **CLAUDE.md** — Engineering constraints and stack decisions

### Scripts to Run
- `scripts/server-setup.sh` — Bootstrap server (once, as root)
- `scripts/deploy.sh` — Deploy/update (recurring, as lipi user)
- `scripts/server-health-check.sh` — Diagnostics (debug issues)

### Configuration
- `docker-compose.yml` — Production stack definition
- `.env.example` → fill in → `.env` (on server)
- `Caddyfile` — HTTPS proxy config (mostly automated)
- `monitoring/prometheus.yml` — Metrics (optional)

---

## ⚡ 3-Step Deployment (30 minutes)

### Step 1: Bootstrap (once, as root)
```bash
ssh root@YOUR_SERVER
curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/lipi/main/scripts/server-setup.sh | bash
reboot  # if GPU driver installed
```

**What it does:**
- Updates system packages
- Installs NVIDIA driver 535 (L40S support)
- Installs Docker + nvidia-container-toolkit
- Configures UFW firewall (22/80/443)
- Creates `lipi` user and clones repo to `/opt/lipi`
- Creates `.env` from `.env.example` (NEEDS FILLING)

### Step 2: Configure (once, as lipi user)
```bash
ssh lipi@YOUR_SERVER
nano /opt/lipi/.env
```

**Fill in these values:**
```bash
CADDY_DOMAIN=yourdomain.com
CADDY_EMAIL=admin@yourdomain.com
APP_URL=https://yourdomain.com

POSTGRES_PASSWORD=<strong_random>
JWT_SECRET=<32_byte_hex>
NEXTAUTH_SECRET=<32_byte_hex>

GOOGLE_CLIENT_ID=<from_google_cloud>
GOOGLE_CLIENT_SECRET=<from_google_cloud>

GROQ_API_KEY=<optional_fallback>
```

**Generate secrets:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 3: Deploy (recurring)
```bash
cd /opt/lipi
bash scripts/deploy.sh
# Or: make deploy
```

**Takes 15 min.** Builds images, starts services, waits for health checks.

---

## 🔍 Verify Deployment

```bash
# Check all services
docker compose ps

# Backend health
curl https://yourdomain.com/api/health | jq

# Full diagnostics
bash scripts/server-health-check.sh
# Or: make server-health
```

All services should show `healthy` or `Up`.

---

## 📊 Service Stack

```
Browser (HTTPS)
  ↓
Caddy (reverse proxy, auto-HTTPS)
  ├─ / → Frontend (Next.js:3000)
  ├─ /api/* → Backend (FastAPI:8000)
  └─ /ws/* → WebSocket (Backend:8000)

Backend communicates with:
  ├─ PostgreSQL:5432 (teacher data, sessions, points)
  ├─ Valkey:6379 (cache, sessions)
  ├─ vLLM:8080 (LLM inference — Qwen3-32B)
  ├─ ML:5001 (STT + TTS microservice)
  └─ MinIO:9000 (audio file storage)

GPU Services (2× L40S):
  ├─ vLLM (loads model at container start, ~5 min)
  └─ ML (faster-whisper on GPU 0, mms-tts on GPU 1)

Optional:
  ├─ Prometheus:9090 (metrics)
  └─ Grafana:3000 (dashboards)
```

---

## 🛠️ Daily Operations

### Check Status
```bash
cd /opt/lipi
make health              # Quick check
make server-health       # Full diagnostics
docker compose logs -f   # Follow logs
```

### Restart Services
```bash
docker compose restart backend    # Fast
docker compose restart vllm       # Slow (~5 min, reloads model)
docker compose down && docker compose up -d  # Full restart
```

### Database Backup
```bash
docker compose exec postgres pg_dump -U lipi lipi | gzip > backup_$(date +%Y%m%d).sql.gz
```

### View Logs
```bash
docker compose logs -f               # All services
docker compose logs -f backend       # FastAPI
docker compose logs -f vllm          # LLM inference
docker compose logs -f ml            # STT + TTS
docker compose logs -f postgres      # Database
```

### Update Code
```bash
cd /opt/lipi
git pull
docker compose build backend frontend ml
docker compose up -d
```

---

## ⚠️ Common Issues & Quick Fixes

| Issue | Fix |
|-------|-----|
| vLLM loading >10 min | Normal — Qwen3-32B is 32GB. Check: `docker compose logs vllm \| tail` |
| Backend returns 503 | vLLM still loading or GPU error. Check logs above. |
| HTTPS certificate failing | Server needs outbound port 443. Check: `curl https://google.com` |
| "Docker socket not accessible" | `sudo usermod -aG docker lipi` and re-login |
| Database won't start | Check: `docker compose logs postgres` |
| GPU passthrough not working | Reboot after driver install. Verify: `nvidia-smi` |

**Full troubleshooting:** See `DEPLOYMENT_QUICK_START.md`, "Troubleshooting" section.

---

## 🎯 Critical Files & Locations

**On server:**
- Repo: `/opt/lipi/`
- Config: `/opt/lipi/.env`
- Docker volumes: `/var/lib/docker/volumes/lipi_*/_data`
- Backups: `/opt/lipi/backups/` (set up cronjob)

**Documentation (local, in this repo):**
- Quick ref: `DEPLOYMENT_README.txt`
- Full guide: `DEPLOYMENT_QUICK_START.md`
- Operations: `OPERATIONS.md`
- Architecture: `DEV_ONBOARDING.md`, `CLAUDE.md`

---

## 🔑 Access & Credentials

**SSH:**
- User: `lipi` (for operations)
- Root: `root` (for first bootstrap only)
- Key or password: (your server setup)

**Database:**
- User: `lipi`
- Password: (from `.env` POSTGRES_PASSWORD)
- Host: `postgres` (Docker-internal)
- Port: `5432` (Docker-internal only, not exposed externally)

**MinIO (object storage):**
- Access key: (from `.env` MINIO_ACCESS_KEY)
- Secret key: (from `.env` MINIO_SECRET_KEY)
- Access: SSH tunnel to port 9001, then http://localhost:9001
- ```bash
  ssh -L 9001:localhost:9001 lipi@YOUR_SERVER
  # Visit http://localhost:9001
  ```

**Monitoring (optional):**
- Prometheus: http://localhost:9090 (SSH tunnel)
- Grafana: http://localhost:3000 (SSH tunnel)

---

## 📞 Escalation Path

If something breaks:

1. **Check logs immediately:**
   ```bash
   docker compose logs -f
   docker compose logs -f <service_name>
   ```

2. **Run diagnostics:**
   ```bash
   bash scripts/server-health-check.sh
   ```

3. **Consult documentation:**
   - `DEPLOYMENT_QUICK_START.md` (Troubleshooting)
   - `OPERATIONS.md` (Recovery procedures)

4. **Emergency restart (last resort):**
   ```bash
   docker compose down -v  # WARNING: deletes all data
   docker compose up -d
   ```

5. **Restore from backup:**
   ```bash
   gunzip < backup_YYYYMMDD.sql.gz | docker compose exec -T postgres psql -U lipi -d lipi
   ```

---

## 🎓 Training Points

- **Caddy**: Auto-HTTPS reverse proxy. No manual cert management needed. Renewal is automatic.
- **vLLM**: Model loads at container start (~5 min first time). Restarting = model reload (~5 min).
- **Valkey**: In-memory cache (not Redis — BSD-3 licensed fork). Used for sessions, leaderboard cache.
- **Groq fallback**: If vLLM is down/loading, STT/LLM calls go to Groq API (if key is set). Transparent to users.
- **WebSocket**: All voice conversations run over a single persistent WS connection per session. Not HTTP polling.
- **Bilingual**: Every user-facing string has Nepali + English. Check `.env` for language-related settings.

---

## 📈 Monitoring (Optional but Recommended)

```bash
cd /opt/lipi
make monitoring  # Start Prometheus + Grafana

# Then access via SSH tunnel
ssh -L 9090:localhost:9090 -L 3000:localhost:3000 lipi@YOUR_SERVER

# Default Grafana credentials: admin / admin (change after login)
```

Key metrics to watch:
- GPU utilization (vLLM should use ~85% of VRAM)
- Backend request latency (target <100ms)
- STT/TTS latency (target <500ms)
- Database query latency
- WebSocket connection count

---

## 🚨 SLA / Uptime Targets

**During production launch:**
- Availability: 99% (downtime budget ~7 min/day)
- Latency: <3s end-to-end (voice in → audio out)
- STT latency: <200ms
- LLM latency: <2s (first token)
- TTS latency: <500ms

**Known limitations:**
- vLLM cold start: 5-8 min (model loads to GPU)
- Single point of failure: both GPUs on one server (Phase 2 will add redundancy)
- Audio storage: MinIO on same server (Phase 2 will add S3-compatible backup)

---

## 🔄 Update Cycle

**Deploying code changes:**

```bash
cd /opt/lipi
git pull origin main
docker compose build backend frontend ml
docker compose up -d
# Services come back online, old containers removed
```

**Deploying config changes:**

```bash
# Edit .env
nano .env

# Restart services that read from .env
docker compose up -d backend
```

**Zero-downtime deployments:**
- Stateless services (frontend, backend) restart quickly
- Frontend: Next.js takes 30s to build + restart
- Backend: uvicorn restarts in 5s
- vLLM: ~5 min (unavoidable, model loads to GPU)

---

## ✅ Handover Checklist

- [ ] You have read `DEPLOYMENT_README.txt`
- [ ] You have read `DEPLOYMENT_QUICK_START.md`
- [ ] You understand the 3-step deployment process
- [ ] You have access to a target server (Ubuntu 22.04, 2× L40S)
- [ ] You have a domain name (for HTTPS)
- [ ] You have Google OAuth credentials
- [ ] You have emergency contact info for infrastructure/escalation
- [ ] You understand the service stack and where each component runs
- [ ] You know how to check logs, restart services, and run backups
- [ ] You have documented any server-specific details (IP, SSH key location, etc.)

---

## 📞 Contact & Questions

For questions about:
- **Deployment scripts**: Check comments in `scripts/server-setup.sh`, `scripts/deploy.sh`
- **Architecture**: Read `DEV_ONBOARDING.md` section 6 or `CLAUDE.md`
- **Operations**: See `OPERATIONS.md`
- **Troubleshooting**: See `DEPLOYMENT_QUICK_START.md` "Troubleshooting"

**Good luck! 🚀 You've got this.**

---

**Handover signed off:** April 14, 2026  
**Status:** Ready for production deployment  
**Blockers:** None. Code is complete and tested.
