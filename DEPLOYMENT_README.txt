================================================================================
LIPI REMOTE SERVER DEPLOYMENT — COMPLETE SETUP
================================================================================

Everything is ready to deploy LIPI to production. This package contains:

📋 DOCUMENTATION (Start here!)
  ├─ DEPLOYMENT_QUICK_START.md    Step-by-step guide (30 min setup)
  ├─ DEPLOY_CHECKLIST.md          Checklist version of above
  ├─ OPERATIONS.md                Daily admin reference
  └─ DEPLOYMENT_SETUP_SUMMARY.md  Overview of what was set up

🔧 SCRIPTS (Run on server)
  ├─ scripts/server-setup.sh      Bootstrap Ubuntu 22.04 (run once as root)
  ├─ scripts/deploy.sh            Production deploy (run as lipi user)
  └─ scripts/server-health-check.sh Full diagnostics (run to debug)

⚙️ CONFIGURATION
  ├─ docker-compose.yml           Production stack (fixed: added APP_URL)
  ├─ docker-compose.dev.yml       Local dev overlay (unchanged)
  ├─ Caddyfile                    HTTPS proxy (auto Let's Encrypt)
  ├─ .env.example                 Environment template
  └─ monitoring/prometheus.yml    Metrics scraping (optional)

💻 CONVENIENCE
  ├─ Makefile                     One-command operations (make deploy, make health)
  └─ README.md                    Updated with deployment links

================================================================================
QUICK START (3 STEPS, 30 MINUTES)
================================================================================

1. BOOTSTRAP SERVER (as root, first time only)
   $ ssh root@YOUR_SERVER
   $ curl -fsSL .../scripts/server-setup.sh | bash
   $ reboot  # if GPU driver installed

2. CONFIGURE
   $ ssh lipi@YOUR_SERVER
   $ nano /opt/lipi/.env
   # Fill in: CADDY_DOMAIN, APP_URL, POSTGRES_PASSWORD, JWT_SECRET,
   #          GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, etc.

3. DEPLOY (recurring updates)
   $ cd /opt/lipi
   $ bash scripts/deploy.sh
   # vLLM cold start takes ~5 min (normal)

Done! Visit https://yourdomain.com

================================================================================
KEY FILES TO READ
================================================================================

For Deployment:       DEPLOYMENT_QUICK_START.md
For Daily Ops:        OPERATIONS.md
For Checklists:       DEPLOY_CHECKLIST.md
For Debugging:        DEPLOYMENT_QUICK_START.md (Troubleshooting section)
For Developers:       DEV_ONBOARDING.md, README_DEV.md

================================================================================
WHAT WAS CREATED/FIXED
================================================================================

✅ Scripts:
   - server-setup.sh: Full Ubuntu bootstrap (Docker, CUDA, UFW, repo)
   - deploy.sh: Production deploy with health checks
   - server-health-check.sh: Complete server diagnostics

✅ Configuration:
   - docker-compose.yml: Added APP_URL, GOOGLE_* env vars (CORS fix)
   - monitoring/prometheus.yml: Metrics scraping (was referenced but missing)
   - Caddyfile: Clarified local_certs for dev/prod

✅ Frontend Fix:
   - next.config.mjs: allowedOrigins now reads production domain

✅ Documentation:
   - DEPLOYMENT_QUICK_START.md: Complete 30-min setup guide
   - OPERATIONS.md: Daily admin reference
   - DEPLOY_CHECKLIST.md: Step-by-step checklist
   - DEPLOYMENT_SETUP_SUMMARY.md: This directory's contents

✅ Convenience:
   - Makefile: make deploy, make health, make logs, etc.

================================================================================
HARDWARE REQUIREMENTS
================================================================================

Server:       Ubuntu 22.04 LTS
RAM:          256GB (recommended for 2× L40S)
Storage:      4TB NVMe
GPUs:         2× NVIDIA L40S (48GB each)
Network:      1 Gbps, ports 22/80/443
Domain:       Required for HTTPS (Let's Encrypt)

================================================================================
ENVIRONMENT VARIABLES NEEDED
================================================================================

REQUIRED:
  CADDY_DOMAIN               yourdomain.com
  CADDY_EMAIL                admin@yourdomain.com
  APP_URL                    https://yourdomain.com
  POSTGRES_PASSWORD          <strong_random>
  JWT_SECRET                 <32_byte_hex>
  NEXTAUTH_SECRET            <32_byte_hex>
  GOOGLE_CLIENT_ID           <from_google_cloud>
  GOOGLE_CLIENT_SECRET       <from_google_cloud>

OPTIONAL:
  GROQ_API_KEY               <fallback_if_vllm_down>
  ENVIRONMENT                production
  LOG_LEVEL                  INFO

Generate JWT secrets:
  python3 -c "import secrets; print(secrets.token_hex(32))"

================================================================================
POST-DEPLOYMENT
================================================================================

Verify:
  curl https://yourdomain.com/api/health | jq
  # All checks should return "true"

Monitor:
  ssh lipi@YOUR_SERVER && make server-health
  # Check all services are "healthy" or "Up"

Logs:
  docker compose logs -f
  # Watch for errors or issues

Backups:
  docker compose exec postgres pg_dump -U lipi lipi | gzip > backup.sql.gz
  # Set up daily cron job

================================================================================
ARCHITECTURE
================================================================================

Browser
  ↓ HTTPS
Caddy (reverse proxy, auto-HTTPS)
  ├─ / → Frontend (Next.js)
  ├─ /api/* → Backend (FastAPI)
  └─ /ws/* → WebSocket (Backend)

Backend (FastAPI)
  ├─ PostgreSQL (data persistence)
  ├─ Valkey (cache & sessions)
  ├─ vLLM:8080 (LLM inference - Qwen3-32B)
  ├─ ML:5001 (STT + TTS)
  └─ MinIO (audio storage)

GPU Services (2× L40S):
  - vLLM tensor-parallel across both GPUs
  - ML service uses GPU 0 (STT), GPU 1 (TTS)

Optional:
  - Prometheus:9090 (metrics)
  - Grafana:3000 (dashboards)

================================================================================
COMMON COMMANDS
================================================================================

ssh lipi@YOUR_SERVER
cd /opt/lipi

# One-command operations
make deploy               # Update and redeploy
make health              # Full health check
make logs                # Follow all logs
make server-health       # Complete diagnostics
make down                # Stop all services
docker compose restart backend  # Restart one service

# Database
make db-shell            # Open psql console
docker compose exec postgres pg_dump -U lipi lipi | gzip > backup.sql.gz

# Monitoring (optional)
make monitoring          # Start Prometheus + Grafana

# MinIO console (SSH tunnel)
ssh -L 9001:localhost:9001 lipi@YOUR_SERVER
# Then visit http://localhost:9001

================================================================================
TROUBLESHOOTING
================================================================================

Problem: vLLM still loading after 10 minutes
  → Normal! Qwen3-32B is 32GB. First load takes 5-8 min. Check:
     docker compose logs vllm | tail -20

Problem: Backend returns 503 error
  → vLLM might still be loading or GPU issue. Check:
     docker compose logs backend
     docker compose logs vllm
     nvidia-smi  # Verify GPUs visible

Problem: Caddy certificate not obtained
  → Server needs outbound HTTPS. Check:
     docker compose logs caddy
     curl https://google.com  # test connectivity

Problem: "Docker socket not accessible"
  → Add lipi user to docker group:
     sudo usermod -aG docker lipi
     # Logout and back in

Problem: Database won't start
  → Check logs:
     docker compose logs postgres
     # If corruption, last resort: docker compose down -v postgres

Full troubleshooting guide: See DEPLOYMENT_QUICK_START.md

================================================================================
NEXT STEPS
================================================================================

1. Read: DEPLOYMENT_QUICK_START.md (complete setup guide)
2. Prepare: Fill in .env with production values
3. Deploy: Run scripts/server-setup.sh on your server
4. Verify: Test https://yourdomain.com in a browser
5. Operate: Use OPERATIONS.md for daily admin tasks

Phase 2 (roadmap): Speaker embeddings, async learning queue, GDPR consent

================================================================================
SUPPORT
================================================================================

Docs:
  - DEPLOYMENT_QUICK_START.md (most issues here)
  - OPERATIONS.md (daily operations)
  - DEV_ONBOARDING.md (architecture)

Check logs:
  docker compose logs -f
  docker compose logs -f backend
  docker compose logs -f vllm

Run diagnostics:
  bash scripts/server-health-check.sh

================================================================================
DONE! 🚀
================================================================================

You're ready to deploy LIPI to production.

Next: Read DEPLOYMENT_QUICK_START.md and follow the 3-step process.

Questions? Check the docs or run: make server-health

Good luck!
