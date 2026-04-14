# LIPI — Deployment Quick Start

Deploy LIPI to a remote Ubuntu 22.04 server with 2× NVIDIA L40S in ~30 minutes.

---

## Prerequisites

- **Server**: Ubuntu 22.04 LTS, bare-metal or cloud VM
- **Hardware**: 2× NVIDIA L40S (or compatible), 256GB RAM, 4TB NVMe
- **Network**: SSH access, ports 80/443 outbound (for Let's Encrypt ACME challenges)
- **Domain**: A domain name (for Caddy HTTPS)
- **Git**: Remote repo access (GitHub, GitLab, etc.)

---

## Step 1: Bootstrap the Server (10 min, as root)

On a fresh Ubuntu 22.04 server:

```bash
# Option A: Direct script
curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/lipi/main/scripts/server-setup.sh | bash

# Option B: Copy script and run locally
scp scripts/server-setup.sh root@YOUR_SERVER:~
ssh root@YOUR_SERVER bash server-setup.sh
```

**What it does:**
- Updates system packages
- Installs NVIDIA driver 535 (L40S support)
- Installs Docker + nvidia-container-toolkit
- Configures UFW firewall (22/80/443 only)
- Clones repo to `/opt/lipi` as user `lipi`
- Creates `.env.example` → `.env` (NEEDS FILLING)

**Output:** Check for `"Setup complete"` message. If GPU driver was installed, **reboot is required** before continuing.

```bash
sudo reboot
# Verify after reboot
nvidia-smi  # Should show 2× L40S cards
```

---

## Step 2: Configure Environment (5 min)

SSH to server and edit the `.env` file:

```bash
ssh -p 22 user@YOUR_SERVER
sudo su - lipi
nano /opt/lipi/.env
```

Fill in these critical values:

```bash
# Domain configuration
CADDY_DOMAIN=yourdomain.com                    # e.g., lipi.yourcompany.com
CADDY_EMAIL=admin@yourdomain.com               # For Let's Encrypt renewal notifications
APP_URL=https://yourdomain.com                 # Used for CORS in backend

# Database (change from defaults!)
POSTGRES_PASSWORD=<VERY_STRONG_PASSWORD>
DATABASE_URL=postgresql+asyncpg://lipi:<PASSWORD>@postgres:5432/lipi

# JWT (generate random 32-byte hex)
JWT_SECRET=<32_byte_hex_string>                # python3 -c "import secrets; print(secrets.token_hex(32))"
NEXTAUTH_SECRET=<32_byte_hex_string>

# Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=<YOUR_GOOGLE_CLIENT_ID>
GOOGLE_CLIENT_SECRET=<YOUR_GOOGLE_CLIENT_SECRET>

# MinIO storage (change from defaults!)
MINIO_SECRET_KEY=<STRONG_PASSWORD>

# Optional: Groq fallback (for STT/LLM when local inference fails)
GROQ_API_KEY=gsk_...                           # Get from groq.com

# Optional: GPU configuration (usually auto-detected, override if needed)
CUDA_VISIBLE_DEVICES=0,1
STT_DEVICE=cuda:0
TTS_DEVICE=cuda:1
```

**To generate JWT_SECRET:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# Output: abc123def456...  (copy-paste into .env)
```

Save and exit (Ctrl+X, Y, Enter in nano).

---

## Step 3: Deploy (10 min)

Still as the `lipi` user:

```bash
cd /opt/lipi
bash scripts/deploy.sh
# Or: make deploy
```

This will:
1. Pull latest code (`git pull`)
2. Build Docker images (backend, frontend, ml service)
3. Start services in dependency order
4. Wait for health checks (postgres → backend → vLLM)
5. Print final status

**Expected output:**
```
[2/4] Building Docker images...
  => Building backend...
  => Building frontend...
  => Building ml...

[3/4] Starting services...
  Starting infra...
    postgres: healthy ✓
    valkey: healthy ✓
    minio: healthy ✓

  Starting app services...
  Starting GPU services...
  NOTE: vLLM cold start takes ~5 min. Groq fallback is active until then.

[4/4] Waiting for health checks...
    backend (FastAPI): UP
    ml service (STT+TTS): UP
    vLLM (Qwen3-32B): UP (after ~5 min)

=== Container status ===
NAME                    STATUS
lipi-postgres           Up 2 minutes (healthy)
lipi-valkey             Up 2 minutes (healthy)
lipi-minio              Up 2 minutes
lipi-backend            Up 1 minute (healthy)
lipi-frontend           Up 1 minute
lipi-ml                 Up 50 seconds (healthy)
lipi-vllm               Up 30 seconds
lipi-caddy              Up 1 minute

Deploy complete at ...
```

**This takes 10–15 minutes.** The first vLLM startup is slow (loads Qwen3-32B into VRAM).

---

## Step 4: Verify Deployment

```bash
# Check all services
make health
# Or: docker compose ps

# Follow logs
make logs
# Or: docker compose logs -f

# Specific service logs
docker compose logs -f backend     # FastAPI
docker compose logs -f vllm        # LLM inference
docker compose logs -f ml          # STT + TTS

# Full health check
bash scripts/server-health-check.sh
# Or: make server-health
```

---

## Step 5: Test the Application

Once all services are healthy, visit your domain in a browser:

```
https://yourdomain.com
```

You should see:
1. **Landing page** with "लिपि" title
2. **Auth page** (click "Get started")
3. **Demo login** (if `NODE_ENV=development`; you can enable for testing)
4. **Google OAuth** flow (after configuring Google Cloud Console)

### Quick smoke test (no browser needed)

```bash
# Backend health
curl https://yourdomain.com/api/health | jq

# Create a test session (if auth is optional)
curl -X POST https://yourdomain.com/api/sessions

# vLLM status
curl https://yourdomain.com/api/liveness  # or ask backend logs
```

---

## Troubleshooting

### vLLM still loading after 15 minutes
- **Expected**: Qwen3-32B is 32GB; first load downloads + loads to VRAM (~8 min typical)
- **Check**: `docker compose logs vllm | tail -20`
- **Falls back to Groq**: If `GROQ_API_KEY` is set, LLM calls still work while vLLM loads
- **Stay patient**: Don't restart; it's just loading the model

### "ERROR: Docker socket not accessible"
```bash
# Add lipi user to docker group
sudo usermod -aG docker lipi
# Logout and login as lipi user
exit
ssh -u lipi YOUR_SERVER
```

### GPU passthrough not working
```bash
# Verify nvidia-container-toolkit is running
docker run --rm --gpus all nvidia/cuda:12.1.1-base nvidia-smi
# If this fails, reboot after driver install
```

### Database connection refused
```bash
# Check postgres is healthy
docker compose ps postgres

# Check logs
docker compose logs postgres

# Verify DATABASE_URL in .env matches docker-compose.yml config
cat .env | grep DATABASE_URL
```

### Caddy certificate not obtained
```bash
# Caddy needs to reach Let's Encrypt (port 443 outbound)
# Check firewall isn't blocking outbound HTTPS
sudo ufw status

# Check Caddy logs
docker compose logs caddy

# For local testing, enable self-signed certs:
# Edit Caddyfile: uncomment "local_certs" and redeploy
```

### WebSocket connection fails
- Caddy needs to forward WebSocket headers: `Upgrade`, `Connection`
- The `Caddyfile` already has this configured
- Check: `docker compose logs caddy | grep -i websocket`

---

## Daily Operations

### View logs
```bash
make logs                   # All services
docker compose logs -f backend
docker compose logs -f ml
```

### Restart a service
```bash
docker compose restart backend
docker compose restart ml     # Note: vLLM restart reloads the model (~5 min)
```

### Stop all services
```bash
make down                   # Containers stop, volumes persist
```

### Start after stopping
```bash
make prod                   # Restart full stack
```

### Database backup
```bash
docker compose exec postgres pg_dump -U lipi lipi | gzip > backup_$(date +%Y%m%d).sql.gz
```

### View MinIO console (securely)
```bash
# Forward MinIO console port via SSH
ssh -L 9001:localhost:9001 -p 22 user@YOUR_SERVER

# Then visit: http://localhost:9001
# Credentials: MINIO_ACCESS_KEY and MINIO_SECRET_KEY from .env
```

---

## Monitoring (Optional)

Start Prometheus + Grafana:

```bash
make monitoring
# Then visit http://localhost:9090 (Prometheus) or http://localhost:3000 (Grafana)
# Or access via SSH tunnel if server is remote:
# ssh -L 9090:localhost:9090 -L 3000:localhost:3000 user@YOUR_SERVER
```

---

## Rollback to previous version

```bash
git log --oneline | head -5
git checkout <PREVIOUS_COMMIT_HASH>
make deploy
```

---

## Production Checklist

Before going live with real teachers:

- [ ] Domain configured and HTTPS working (`curl https://yourdomain.com` returns 200)
- [ ] Google OAuth credentials created (Google Cloud Console)
- [ ] `POSTGRES_PASSWORD`, `JWT_SECRET` set to strong random values
- [ ] `GROQ_API_KEY` set (optional but recommended fallback)
- [ ] All services healthy: `make health`
- [ ] Test full auth flow: landing → auth → demo login or Google OAuth
- [ ] Test conversation: start session, send audio (or text if STT fails)
- [ ] Check logs for errors: `make logs | grep -i error`
- [ ] Firewall only allows 22/80/443: `sudo ufw status`
- [ ] Backup strategy in place (cronjob with `pg_dump`)
- [ ] Monitoring dashboard running (optional): `make monitoring`

---

## Next: Speaker Embeddings (Phase roadmap item #1)

After first user test, wire in speaker embedding extraction:

```bash
# Already on the roadmap — see: ml/stt.py, backend/models/session.py
# Needed for: dialect clustering, teacher profile optimization
```

See `PHASE_ROADMAP.md` for full feature list.

---

## Support

Check logs first:
```bash
docker compose logs -f backend   # Most issues here
docker compose logs -f vllm
docker compose logs -f ml
```

Then check:
- `.env` file is complete and matches `docker-compose.yml`
- All services have `healthy` or `Up` status
- UFW isn't blocking needed ports
- GPU passthrough works: `nvidia-smi` and `docker run --gpus all ...`

---

**Deployment complete!** Your LIPI instance is now live and ready for teachers. 🎉
