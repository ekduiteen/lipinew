# Remote Server Setup — Complete Summary

Everything needed to deploy LIPI to production. All files created, tested, and ready to use.

---

## 📦 What Was Created

### Scripts (in `scripts/`)

| File | Purpose | Run as |
|------|---------|--------|
| **server-setup.sh** | Ubuntu 22.04 bootstrap: Docker, NVIDIA drivers, UFW, repo clone | `root` (first time) |
| **deploy.sh** | Production deploy: git pull, build, start services, health checks | `lipi` user (recurring) |
| **server-health-check.sh** | Full server diagnostics: GPUs, services, databases, certificates | `lipi` user (debugging) |

### Configuration

| File | Purpose |
|------|---------|
| **docker-compose.yml** | Production stack (fixed) — unchanged |
| **docker-compose.dev.yml** | Local dev overlay — unchanged |
| **Caddyfile** | Reverse proxy with auto-HTTPS (via Let's Encrypt) |
| **.env.example** | Environment template — fill in values before deploy |
| **monitoring/prometheus.yml** | Metrics scraping (prometheus + grafana) |

### Documentation

| File | Audience |
|------|----------|
| **DEPLOYMENT_QUICK_START.md** | DevOps / anyone deploying to production |
| **OPERATIONS.md** | Daily operations reference for admins |
| **Makefile** | Everyone — one-command operations |

### Code Fixes

| File | What was fixed |
|------|--------|
| **docker-compose.yml** | Added `APP_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` to backend env (CORS fix) |
| **frontend/next.config.mjs** | Fixed `allowedOrigins` to read production domain from `NEXTAUTH_URL` |
| **Caddyfile** | Clarified `local_certs` comment for dev vs prod |

---

## 🎯 Quick Deploy Sequence

### 1️⃣ Bootstrap Server (once, as root)

```bash
ssh root@YOUR_SERVER
curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/lipi/main/scripts/server-setup.sh | bash
sudo reboot  # If GPU driver was installed
```

**Output**: 
- Docker + NVIDIA drivers installed
- UFW firewall configured (22/80/443)
- Repo cloned to `/opt/lipi`
- `.env` file created (needs filling)

### 2️⃣ Configure (once, as lipi user)

```bash
ssh lipi@YOUR_SERVER
nano /opt/lipi/.env

# Fill in:
#   CADDY_DOMAIN=yourdomain.com
#   CADDY_EMAIL=admin@yourdomain.com
#   APP_URL=https://yourdomain.com
#   POSTGRES_PASSWORD=<strong>
#   JWT_SECRET=<random_hex_32_bytes>
#   GOOGLE_CLIENT_ID=...
#   GOOGLE_CLIENT_SECRET=...
#   GROQ_API_KEY=... (optional fallback)
```

### 3️⃣ Deploy (recurring updates)

```bash
cd /opt/lipi
bash scripts/deploy.sh
# Or: make deploy
```

**Takes ~15 minutes.** Builds images, starts services, waits for health checks.

---

## 📊 Service Architecture

```
Browser (HTTPS) 
    ↓
Caddy (reverse proxy, auto-HTTPS)
    ├─ /       → Frontend (Next.js:3000)
    ├─ /api/*  → Backend (FastAPI:8000)
    └─ /ws/*   → WebSocket (Backend:8000)

Backend (FastAPI:8000) 
    ├─ → PostgreSQL:5432 (data)
    ├─ → Valkey:6379 (cache)
    ├─ → vLLM:8080 (LLM inference)
    ├─ → ML:5001 (STT + TTS)
    └─ → MinIO:9000 (object storage)

GPU Services (shared 2× L40S)
    ├─ vLLM (Qwen3-32B, tensor-parallel across GPUs)
    └─ ML (faster-whisper STT + mms-tts-npi TTS)

Optional Monitoring
    ├─ Prometheus:9090 (metrics collection)
    └─ Grafana:3000 (dashboards)
```

---

## 🔧 Daily Operations

```bash
# View logs
make logs

# Check health
make server-health
# Or: docker compose ps

# Full status
curl https://yourdomain.com/api/health | jq

# Restart a service
docker compose restart backend

# Database backup
docker compose exec postgres pg_dump -U lipi lipi | gzip > backup.sql.gz

# SSH to admin console (MinIO, pgAdmin, etc.)
ssh -L 9001:localhost:9001 lipi@YOUR_SERVER
# Then visit http://localhost:9001 (MinIO dashboard)
```

See `OPERATIONS.md` for the complete reference.

---

## ✅ Pre-Deployment Checklist

- [ ] `.env` file filled with production values
- [ ] CADDY_DOMAIN points to your actual domain
- [ ] GOOGLE_CLIENT_ID/SECRET obtained from Google Cloud Console
- [ ] JWT_SECRET and NEXTAUTH_SECRET are strong random values
- [ ] POSTGRES_PASSWORD is strong and random
- [ ] Server can reach Let's Encrypt (port 443 outbound)
- [ ] Firewall allows 22/80/443 only

---

## 🚨 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "vLLM still loading" (15+ min) | Normal — Qwen3-32B is 32GB, first load takes 5–8 min |
| "Docker socket not accessible" | `sudo usermod -aG docker lipi` and re-login |
| "GPU passthrough failed" | Check `nvidia-smi`, reboot if driver was just installed |
| "Database connection refused" | Check postgres is healthy: `docker compose ps postgres` |
| "Caddy certificate not obtained" | Check outbound HTTPS works, see `docker compose logs caddy` |
| "Backend health check stuck" | Check logs: `docker compose logs backend` |

See `DEPLOYMENT_QUICK_START.md`, "Troubleshooting" section for more.

---

## 📈 Monitoring (Optional)

```bash
# Start Prometheus + Grafana
make monitoring

# Access (via SSH tunnel if remote):
ssh -L 9090:localhost:9090 -L 3000:localhost:3000 lipi@YOUR_SERVER

# Then visit:
#   http://localhost:9090 (Prometheus)
#   http://localhost:3000 (Grafana, default: admin/admin)
```

---

## 🔐 Security Notes

- **Firewall**: UFW blocks all ports except 22/80/443. Internal services (5432, 6379, 8000, 8080, 5001, 9000) are Docker-internal only.
- **HTTPS**: Caddy auto-obtains Let's Encrypt certs. Renewal is automatic.
- **Database**: PostgreSQL has strong password (from .env). No external access.
- **Secrets**: All in `.env` (which is `.gitignore`d). Never commit secrets.
- **Admin console**: MinIO is accessible via SSH tunnel only (no external port 9001).

---

## 📝 Files Reference

### To Read First
1. **DEPLOYMENT_QUICK_START.md** — Complete deployment walkthrough
2. **Makefile** — All available commands
3. **.env.example** — All environment variables explained

### If Issues Occur
- **OPERATIONS.md** — Troubleshooting, logs, emergency recovery
- **docker-compose.yml** — Service definitions and health checks
- **CLAUDE.md** — Engineering constraints and architecture rules

### For Developers
- **DEV_ONBOARDING.md** — Local setup, code patterns, database schema
- **README_DEV.md** — Frontend + backend dev servers locally
- **docker-compose.dev.yml** — Local dev overlay

---

## 🎯 Next Steps

1. **Deploy to server** — Follow `DEPLOYMENT_QUICK_START.md`
2. **Test with real users** — Monitor logs, check `make server-health`
3. **Enable speaker embeddings** — Phase roadmap item #1 (STT → embedding vector(512) → DB)
4. **Set up backups** — Automated PostgreSQL dumps to object storage
5. **Enable monitoring** — `make monitoring` for Prometheus + Grafana

---

## 📞 Support Resources

- **Logs**: `make logs` or `docker compose logs -f <service>`
- **Docs**: Start with `DEPLOYMENT_QUICK_START.md`
- **Quick ref**: `OPERATIONS.md` has all admin commands
- **Architecture**: `DEV_ONBOARDING.md` section 6 (conversation flow)

---

**You're ready to deploy!** 🚀

Next: Fill in `.env` and run `bash scripts/server-setup.sh` on your server.
