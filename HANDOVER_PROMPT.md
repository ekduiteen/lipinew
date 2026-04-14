# LIPI Deployment — Handover Prompt

**Copy this prompt and send it to the DevOps engineer or next agent taking over LIPI deployment.**

---

## Handover Prompt for DevOps / Operations Team

```
You are taking over the LIPI deployment. LIPI is a community-powered Nepali 
language learning platform built on FastAPI + Next.js + GPU inference.

STATUS: 
  ✅ Code is complete and tested (Phases 0-3 done)
  ✅ Docker stack is defined and working
  ✅ Deployment scripts are written and tested
  ✅ Documentation is complete
  ❌ Not yet deployed to production

YOUR MISSION:
  Deploy LIPI to a remote Ubuntu 22.04 server with 2× NVIDIA L40S GPUs.
  Make it available to teachers at a public domain.

TIMELINE:
  ~30 minutes total (5 min bootstrap, 5 min config, 15 min deploy, 5 min verify)

WHAT'S READY FOR YOU:

1. Scripts (in scripts/ folder):
   - server-setup.sh      Bootstrap Ubuntu 22.04 (Docker, drivers, firewall, repo)
   - deploy.sh            Production deploy (git pull, build, start services)
   - server-health-check.sh Full server diagnostics (for debugging)

2. Documentation (read in this order):
   - HANDOVER_TO_DEVOPS.md    Complete operations manual for you
   - DEPLOYMENT_README.txt    Quick 1-page reference
   - DEPLOYMENT_QUICK_START.md Full 30-min walkthrough
   - DEPLOY_CHECKLIST.md      Step-by-step checklist (printable)
   - OPERATIONS.md            Daily admin reference
   - MAKE               One-command shortcuts (make deploy, make health, make logs)

3. Configuration (already fixed):
   - docker-compose.yml   ✅ Fixed (added APP_URL, GOOGLE_* env vars)
   - .env.example         ✅ Template ready (fill in values)
   - Caddyfile            ✅ HTTPS proxy configured
   - monitoring/prometheus.yml ✅ Metrics scraping ready

YOUR NEXT STEPS:

1. Read: HANDOVER_TO_DEVOPS.md (this is your complete manual)

2. Prepare:
   - Target server: Ubuntu 22.04 LTS with 2× NVIDIA L40S, 256GB RAM, 4TB NVMe
   - Domain name (for HTTPS via Let's Encrypt)
   - Google OAuth credentials (from Google Cloud Console)
   - SSH access to server

3. Deploy (3 commands):
   
   # Step 1: Bootstrap server (once, as root)
   ssh root@YOUR_SERVER
   curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/lipi/main/scripts/server-setup.sh | bash
   reboot  # if GPU driver installed
   
   # Step 2: Configure (once, as lipi user)
   ssh lipi@YOUR_SERVER
   nano /opt/lipi/.env
   # Fill in: CADDY_DOMAIN, APP_URL, POSTGRES_PASSWORD, JWT_SECRET, 
   #          GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
   
   # Step 3: Deploy (recurring)
   cd /opt/lipi
   bash scripts/deploy.sh
   # Takes ~15 min (vLLM cold start = 5-8 min is normal)

4. Verify:
   curl https://yourdomain.com/api/health | jq
   # All checks should return "true"

5. Monitor daily:
   make health              # Quick status
   make server-health       # Full diagnostics
   docker compose logs -f   # Follow logs
   make logs                # Same as above

IMPORTANT CONSTRAINTS:

- Stack is locked: FastAPI, Next.js 14, vLLM, Qwen3-32B, faster-whisper, mms-tts-npi
- Valkey (NOT Redis) — BSD-3 licensed fork
- Caddy (NOT nginx) — auto-HTTPS via Let's Encrypt
- All secrets in .env (gitignored, never committed)
- WebSocket conversations are persistent (not HTTP polling)
- Database is PostgreSQL 16 + pgvector
- GPU allocation: vLLM on both L40S (tensor-parallel), ML on GPU 0-1

ARCHITECTURE (HIGH LEVEL):

Browser (HTTPS)
  ↓
Caddy (reverse proxy, auto-HTTPS)
  ├─ / → Frontend (Next.js)
  ├─ /api/* → Backend (FastAPI)
  └─ /ws/* → WebSocket (FastAPI)
    ↓
Backend (FastAPI:8000)
  ├─ PostgreSQL:5432 (teacher data, sessions, points)
  ├─ Valkey:6379 (cache, sessions, leaderboard)
  ├─ vLLM:8080 (LLM inference — Qwen3-32B)
  ├─ ML:5001 (STT + TTS microservice)
  └─ MinIO:9000 (audio file storage)

GPU Services (2× L40S):
  ├─ vLLM (Qwen3-32B, tensor-parallel across both GPUs)
  └─ ML (faster-whisper on GPU 0, mms-tts on GPU 1)

COMMON ISSUES & QUICK FIXES:

- vLLM loading >10 min?      Normal — Qwen3-32B is 32GB. Check: docker compose logs vllm | tail
- Backend returns 503?        vLLM still loading. Check logs above.
- Caddy cert not obtained?    Need outbound HTTPS. Check: curl https://google.com
- Docker socket error?        sudo usermod -aG docker lipi (then logout/login)
- Database won't start?       Check: docker compose logs postgres

For full troubleshooting: See DEPLOYMENT_QUICK_START.md "Troubleshooting"

WHAT YOU'LL NEED TO KNOW:

- How to check logs: docker compose logs -f [service]
- How to restart services: docker compose restart backend (fast) or docker compose restart vllm (slow)
- How to backup DB: docker compose exec postgres pg_dump -U lipi lipi | gzip > backup.sql.gz
- How to access MinIO: SSH tunnel to port 9001, credentials in .env
- How to monitor: make monitoring (starts Prometheus + Grafana)

AFTER DEPLOYMENT:

1. Run daily health checks: make health or bash scripts/server-health-check.sh
2. Monitor logs for errors: docker compose logs -f | grep ERROR
3. Set up database backups (cronjob running pg_dump daily)
4. Enable Prometheus + Grafana (optional but recommended)
5. Document any server-specific details (IP, SSH key, domain, etc.)

FILES YOU'LL REFERENCE:

On your local machine:
  - HANDOVER_TO_DEVOPS.md     ← Read this first (your complete manual)
  - DEPLOYMENT_QUICK_START.md ← Full step-by-step
  - OPERATIONS.md             ← Daily operations

On the server (/opt/lipi/):
  - .env                      ← Configuration (keep secret)
  - docker-compose.yml        ← Service definitions
  - scripts/                  ← Deployment scripts
  - Makefile                  ← One-command shortcuts

ESCALATION:

If something breaks:
1. Check logs: docker compose logs -f
2. Run diagnostics: bash scripts/server-health-check.sh
3. Consult OPERATIONS.md (recovery procedures)
4. Restore from backup if needed

YOU'RE READY TO START!

Next: Read HANDOVER_TO_DEVOPS.md and follow the 3-step deployment process.

Questions? Everything is documented in:
  - HANDOVER_TO_DEVOPS.md (operations manual)
  - DEPLOYMENT_QUICK_START.md (setup guide)
  - OPERATIONS.md (daily admin reference)

Good luck! 🚀
```

---

## How to Use This Prompt

1. **Copy the text above** (the section between the triple backticks)
2. **Send to the DevOps engineer** or next agent taking over
3. **They read it** and start with HANDOVER_TO_DEVOPS.md
4. **Done!** They have everything they need to deploy LIPI

---

## Alternative: Short Version (for busy people)

```
LIPI is ready to deploy. It's a Nepali language learning platform (FastAPI + 
Next.js + vLLM + GPUs). Code is done, scripts are ready.

Your job: Deploy to Ubuntu 22.04 server with 2× L40S.

Timeline: ~30 minutes (bootstrap + config + deploy).

What to do:
1. Read: HANDOVER_TO_DEVOPS.md
2. Run: scripts/server-setup.sh (bootstrap)
3. Fill: .env (config)
4. Run: scripts/deploy.sh (deploy)
5. Test: curl https://yourdomain.com/api/health

Questions? See OPERATIONS.md (daily admin) or DEPLOYMENT_QUICK_START.md 
(full guide).

Stack: FastAPI, Next.js, vLLM (Qwen3-32B), faster-whisper, PostgreSQL, 
Valkey, MinIO, Caddy.

Go! 🚀
```

---

## How It Was Done

This handover is complete because:
✅ All code is written and tested
✅ Docker stack is defined
✅ Deployment scripts are automated
✅ Documentation covers every step
✅ Troubleshooting guide is included
✅ Operations manual exists
✅ One-command shortcuts (Makefile) are ready

**The DevOps engineer has everything they need. No additional work required.**
