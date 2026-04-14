# LIPI Deployment Checklist

Complete step-by-step guide to deploy to production. Print or check off as you go.

---

## Phase 1: Pre-Deployment (Local)

### Step 1: Verify Code State
- [ ] All code is committed to git (`git status` shows "clean")
- [ ] Latest code is pushed to remote (`git push`)
- [ ] No sensitive data in commits (search for "password", "secret", "key")
- [ ] `.env` file is in `.gitignore` (should not be tracked)

### Step 2: Verify Docker Images Build
- [ ] Run locally: `docker compose build backend frontend ml`
- [ ] All images build without errors
- [ ] Check image sizes are reasonable (~500MB backend, ~200MB frontend, ~3GB ml)

### Step 3: Prepare Environment Variables
- [ ] Generate strong random values:
  ```bash
  # JWT_SECRET (32-byte hex)
  python3 -c "import secrets; print(secrets.token_hex(32))"
  
  # NEXTAUTH_SECRET (32-byte hex)
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] Prepare Google OAuth credentials:
  - [ ] Project created in Google Cloud Console
  - [ ] OAuth consent screen configured
  - [ ] OAuth 2.0 credentials (Web application type) created
  - [ ] Authorized redirect URI: `https://yourdomain.com/api/auth/google`
  - [ ] Note `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

---

## Phase 2: Server Setup (First Time Only)

### Step 4: SSH Access
- [ ] SSH key added to server (or password auth configured)
- [ ] Test SSH connection: `ssh -p 22 root@YOUR_SERVER`
- [ ] Confirm you can become root: `sudo su -` (or already root)

### Step 5: Run Bootstrap Script
- [ ] Download or copy bootstrap script to server
- [ ] Run: `bash server-setup.sh`
- [ ] Wait for completion message `"=== Setup complete at ..."`
- [ ] Check for errors (any non-zero exit codes should be fixed)

**Expected output includes:**
```
GPU passthrough test...
  (lists 2× L40S cards)
UFW status:
  Status: active
  22/tcp  ALLOW (SSH)
  80/tcp  ALLOW (HTTP)
  443/tcp ALLOW (HTTPS)
```

### Step 6: Reboot (if GPU driver was installed)
- [ ] SSH to server: `ssh root@YOUR_SERVER`
- [ ] Run: `reboot`
- [ ] Wait 2-3 minutes for server to come back online
- [ ] Test SSH connection again

### Step 7: Verify GPU Access
```bash
ssh root@YOUR_SERVER
nvidia-smi
# Should show 2× L40S cards with full VRAM

docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
# Should show GPU 0 and 1 are accessible from Docker
```
- [ ] Both commands show 2× L40S cards
- [ ] GPU memory matches (48GB each = 96GB total)

---

## Phase 3: Configuration (Local)

### Step 8: Prepare .env File
- [ ] Copy `.env.example` to `.env.production` (or similar name for backup)
- [ ] Fill in all required fields:

```bash
# === REQUIRED ===
CADDY_DOMAIN=yourdomain.com
CADDY_EMAIL=admin@yourdomain.com
APP_URL=https://yourdomain.com

POSTGRES_PASSWORD=<STRONG_RANDOM>
JWT_SECRET=<32_BYTE_HEX_FROM_ABOVE>
NEXTAUTH_SECRET=<32_BYTE_HEX_FROM_ABOVE>

GOOGLE_CLIENT_ID=<FROM_GOOGLE_CLOUD>
GOOGLE_CLIENT_SECRET=<FROM_GOOGLE_CLOUD>

# === OPTIONAL BUT RECOMMENDED ===
GROQ_API_KEY=gsk_...  # LLM fallback if vLLM fails
ENVIRONMENT=production
LOG_LEVEL=INFO

# === CHECK DEFAULTS ===
# All other values should be left as-is from .env.example
# (POSTGRES_USER=lipi, VALKEY_URL=valkey://valkey:6379/0, etc.)
```

- [ ] Double-check each value is filled in (no placeholders like "change_me")
- [ ] Domain matches your actual domain (with HTTPS protocol)
- [ ] JWT secrets are 32-byte hex (no spaces, quotes, etc.)
- [ ] Google credentials are copy-pasted exactly

---

## Phase 4: Deploy to Server

### Step 9: Copy .env to Server
```bash
scp /path/to/.env root@YOUR_SERVER:/tmp/
```
- [ ] .env copied successfully

### Step 10: SSH to Server and Move .env
```bash
ssh root@YOUR_SERVER
mv /tmp/.env /opt/lipi/.env
chown lipi:lipi /opt/lipi/.env
chmod 600 /opt/lipi/.env
```
- [ ] .env is now in `/opt/lipi/.env`
- [ ] Owned by user `lipi`
- [ ] Permissions are `600` (not world-readable)

### Step 11: Run Deploy Script
```bash
ssh lipi@YOUR_SERVER
cd /opt/lipi
bash scripts/deploy.sh
```

**This will:**
- [ ] Pull latest git code
- [ ] Build Docker images (backend, frontend, ml)
- [ ] Start PostgreSQL, Valkey, MinIO (wait for health)
- [ ] Start backend, frontend
- [ ] Start vLLM (Qwen3-32B loading — ~5 min)
- [ ] Start ML service (faster-whisper — ~2 min)
- [ ] Start Caddy (HTTPS proxy)

**Expected timing:**
- Image builds: 3-5 min (depends on network)
- Service startup (infra): 2 min
- Service startup (app): 1 min
- vLLM cold start: 5-8 min (model loads to GPU)
- ML service startup: 2 min
- **Total: 15-20 minutes**

### Step 12: Monitor Deployment
- [ ] Watch logs live: `make logs` or `docker compose logs -f`
- [ ] Look for "healthy" status on key services:
  - [ ] postgres: healthy
  - [ ] valkey: healthy
  - [ ] minio: healthy
  - [ ] backend: healthy
  - [ ] ml: healthy
  - [ ] vllm: UP (after ~5 min)

### Step 13: Verify Services are Running
```bash
ssh lipi@YOUR_SERVER
cd /opt/lipi
docker compose ps
```

All should show status "Up" or "(healthy)":
- [ ] lipi-postgres: healthy
- [ ] lipi-valkey: healthy
- [ ] lipi-minio: healthy
- [ ] lipi-backend: healthy
- [ ] lipi-frontend: Up
- [ ] lipi-ml: healthy
- [ ] lipi-vllm: Up (may still be loading)
- [ ] lipi-caddy: Up

---

## Phase 5: Post-Deployment Verification

### Step 14: Test HTTPS Access
```bash
# From your local machine
curl -I https://yourdomain.com
# Should return: HTTP/1.1 200 OK
# And show certificate details (not self-signed)
```
- [ ] HTTPS works without certificate warnings
- [ ] Caddy is routing to frontend correctly

### Step 15: Test Backend API
```bash
curl https://yourdomain.com/api/health | jq
```

**Expected output:**
```json
{
  "status": "ok",
  "environment": "production",
  "database": true,
  "valkey": true,
  "vllm": true,
  "ml_service": true
}
```

- [ ] All checks return `true`
- [ ] vLLM check may be false if still loading (check logs: `docker compose logs vllm`)

### Step 16: Manual Smoke Test (Web Browser)
1. Open browser: `https://yourdomain.com`
2. [ ] Landing page loads (लिपि title visible)
3. [ ] Click "Get started" → redirects to `/auth`
4. [ ] Auth page loads (Google OAuth button visible)
5. [ ] (If NODE_ENV=development) Demo button visible
6. [ ] Google OAuth flow works (starts Google login)

### Step 17: Check Logs for Errors
```bash
# Look for ERROR or WARN messages
docker compose logs | grep -i error
# Should return nothing or only non-critical warnings
```
- [ ] No critical errors in logs

### Step 18: Database is Initialized
```bash
ssh lipi@YOUR_SERVER
docker compose exec postgres psql -U lipi -d lipi -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema='public';"
```
- [ ] Returns a number > 10 (schema tables created)

---

## Phase 6: Operational Setup

### Step 19: Configure Backups (Recommended)
```bash
# On the server, create backup script
cat > /opt/lipi/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/lipi/backups"
mkdir -p "$BACKUP_DIR"
docker compose exec postgres pg_dump -U lipi lipi | gzip > "$BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql.gz"
# Keep only last 7 days
find "$BACKUP_DIR" -mtime +7 -delete
EOF

chmod +x /opt/lipi/backup.sh

# Add to crontab (runs daily at 2 AM)
(crontab -l 2>/dev/null || echo "") | { cat; echo "0 2 * * * /opt/lipi/backup.sh"; } | crontab -
```
- [ ] Backup script created
- [ ] Crontab entry added

### Step 20: Enable Monitoring (Optional but Recommended)
```bash
ssh lipi@YOUR_SERVER
cd /opt/lipi
docker compose --profile monitoring up -d
```
- [ ] Prometheus available at port 9090
- [ ] Grafana available at port 3000
- [ ] (Access via SSH tunnel: `ssh -L 9090:localhost:9090 -L 3000:localhost:3000 lipi@YOUR_SERVER`)

### Step 21: Document Admin Access Points
Create a secure document with:
- [ ] Server IP/hostname
- [ ] SSH user (`lipi`)
- [ ] SSH key or password
- [ ] Domain name
- [ ] Google OAuth credentials location
- [ ] `.env` file location (`/opt/lipi/.env`)
- [ ] MinIO console access (via SSH tunnel, credentials in `.env`)
- [ ] Database credentials (PostgreSQL in `.env`)
- [ ] Caddy data location (`/var/lib/docker/volumes/lipi_caddy_data/_data`)

---

## Phase 7: Ongoing Operations

### Step 22: First Week Monitoring
- [ ] Check server health daily: `ssh lipi@YOUR_SERVER && make server-health`
- [ ] Monitor logs for errors: `docker compose logs | grep ERROR`
- [ ] Confirm Caddy certificate renewal (should auto-renew 30 days before expiry)
- [ ] Test a full conversation (audio in, text out, audio response)

### Step 23: Documentation & Handoff
- [ ] Print or save `OPERATIONS.md` for the operations team
- [ ] Print or save `DEPLOYMENT_QUICK_START.md` as a reference
- [ ] Ensure backup process is documented
- [ ] Ensure escalation path is documented (who to contact if something breaks)

### Step 24: Plan Next Features
- [ ] Speaker embeddings (extract `vector(512)` from each utterance)
- [ ] Async learning queue (replace `asyncio.create_task` with Valkey-backed queue)
- [ ] Automated monitoring alerts
- [ ] Load testing to find bottlenecks

---

## 🎉 Deployment Complete!

Your LIPI instance is now live and ready for teachers.

**Final Checklist:**
- [ ] Domain resolves to HTTPS
- [ ] Landing page loads
- [ ] API health check returns all `true`
- [ ] Logs show no critical errors
- [ ] Database is initialized
- [ ] Backups are running
- [ ] Monitoring is active (optional)

**To verify everything is working:**

```bash
ssh lipi@YOUR_SERVER
cd /opt/lipi
bash scripts/server-health-check.sh
```

Should show:
- [ ] All services running
- [ ] All health checks passing
- [ ] GPUs visible and available
- [ ] Disk space adequate (>1TB free)
- [ ] No recent errors

---

## Troubleshooting Quick Links

| Problem | Quick Fix |
|---------|-----------|
| vLLM still loading | Wait, normal: `docker compose logs vllm \| tail` |
| API returns 503 | Check `docker compose logs backend`, may need Groq API key |
| HTTPS certificate failing | Check outbound port 443: `curl https://google.com` |
| Database won't start | Check logs: `docker compose logs postgres` |
| "Docker socket not accessible" | `sudo usermod -aG docker lipi && logout/login` |

See `DEPLOYMENT_QUICK_START.md` "Troubleshooting" for full reference.

---

**Questions?** See:
- `DEPLOYMENT_QUICK_START.md` — Full deployment guide
- `OPERATIONS.md` — Daily operations reference
- `DEV_ONBOARDING.md` — Architecture overview

Good luck! 🚀
