# LIPI — Operations Reference

Daily admin commands for running LIPI in production.

---

## Quick Status

```bash
# Full health check
make server-health

# Container status
docker compose ps

# Backend health endpoint
curl https://yourdomain.com/api/health | jq
```

---

## Logs & Debugging

```bash
# All services, live
make logs

# Specific service
docker compose logs -f backend     # FastAPI + WebSocket
docker compose logs -f ml          # STT + TTS
docker compose logs -f vllm        # LLM inference
docker compose logs -f postgres    # Database
docker compose logs -f caddy        # HTTPS proxy + routing

# Last N lines
docker compose logs backend --tail 50

# Search logs
docker compose logs | grep "ERROR"
docker compose logs vllm | grep "error"
```

---

## Restarting Services

```bash
# Restart one service (fast, keeps others running)
docker compose restart backend

# Graceful restart (stop then start)
docker compose stop backend
docker compose start backend

# Full restart (all services)
docker compose down
docker compose up -d

# ⚠️ WARNING: Restarting vLLM takes ~5 min (reloads 32GB model)
docker compose restart vllm
```

---

## Deployments

```bash
# Deploy latest code (pull, build, restart)
make deploy
# Or manually:
cd /opt/lipi && bash scripts/deploy.sh

# Update one service only (e.g., after code change to backend)
docker compose build backend
docker compose up -d backend
```

---

## Database Operations

```bash
# Open psql shell
make db-shell
# Or: docker compose exec postgres psql -U lipi -d lipi

# Backup
docker compose exec postgres pg_dump -U lipi lipi | gzip > backup.sql.gz

# Restore from backup
gunzip < backup.sql.gz | docker compose exec -T postgres psql -U lipi -d lipi

# Reset database (DESTROYS ALL DATA)
docker compose down -v postgres
docker compose up -d postgres
```

---

## Cache / Session Store (Valkey)

```bash
# Open CLI
make valkey-shell
# Or: docker compose exec valkey valkey-cli

# Check keys
DBSIZE                    # Total keys
KEYS *                    # List all (careful in prod!)
GET lipi:session:xyz      # Get session data
TTL lipi:session:xyz      # Time to live

# Clear cache (careful!)
FLUSHDB                   # Clear current DB
FLUSHALL                  # Clear all DBs
```

---

## Object Storage (MinIO)

```bash
# Admin console
# 1. SSH tunnel: ssh -L 9001:localhost:9001 user@server
# 2. Visit: http://localhost:9001
# 3. Login with MINIO_ACCESS_KEY / MINIO_SECRET_KEY from .env

# Or use MinIO CLI
docker compose exec minio mc admin info lipi

# List buckets
docker compose exec minio mc ls lipi/

# List audio files
docker compose exec minio mc ls lipi/lipi-audio/

# Remove old files
docker compose exec minio mc rm --recursive --older-than 30d lipi/lipi-audio/
```

---

## Performance & Monitoring

```bash
# Container resource usage
docker compose stats

# GPU utilization
nvidia-smi                       # Live GPU stats
nvidia-smi --query-gpu=name,utilization.gpu --format=csv --loop-ms=1000

# CPU/Memory on server
top -b -n 1 | head -20
free -h
df -h

# Network connections
ss -tlnp | grep -E ":80|:443|:8000|:5001|:8080|:5432"
```

---

## Firewall & Security

```bash
# Check UFW rules
sudo ufw status verbose

# Allow/deny access
sudo ufw allow 22/tcp
sudo ufw deny 5432/tcp

# View recent failed connection attempts
sudo journalctl -u ufw -n 20
```

---

## Certificate Management (HTTPS)

```bash
# Caddy handles Let's Encrypt automatically
# Certificates stored in: /var/lib/docker/volumes/lipi_caddy_data/_data

# Check certificate expiry
docker compose logs caddy | grep -i certificate

# Manual cert renewal (rarely needed)
docker compose exec caddy caddy reload

# For local testing with self-signed certs:
# 1. Edit Caddyfile: uncomment "local_certs"
# 2. docker compose restart caddy
```

---

## User Management (Future)

```bash
# Check users in database
docker compose exec postgres psql -U lipi -d lipi -c "SELECT id, first_name, email, onboarding_completed_at FROM users;"

# Delete a user (if needed for GDPR)
docker compose exec postgres psql -U lipi -d lipi -c "DELETE FROM users WHERE id='<USER_ID>';"

# Reset a user's data (sessions, points, badges)
# See DATABASE_SCHEMA.md for cascading deletes
```

---

## Statistics & Analytics

```bash
# Total users
docker compose exec postgres psql -U lipi -d lipi -c "SELECT COUNT(*) FROM users;"

# Active sessions (live conversations)
docker compose exec postgres psql -U lipi -d lipi -c "SELECT COUNT(*) FROM teaching_sessions WHERE ended_at IS NULL;"

# Total points distributed
docker compose exec postgres psql -U lipi -d lipi -c "SELECT SUM(final_points) FROM points_transactions;"

# Top teachers (by points this month)
docker compose exec postgres psql -U lipi -d lipi << 'SQL'
SELECT first_name, points_this_month FROM users
JOIN teacher_points_summary ON users.id = teacher_points_summary.teacher_id
ORDER BY points_this_month DESC LIMIT 10;
SQL
```

---

## Monitoring (Optional)

```bash
# Start Prometheus + Grafana
make monitoring

# Then access:
# - Prometheus: http://localhost:9090 (or SSH tunnel -L 9090:localhost:9090)
# - Grafana: http://localhost:3000 (default password: admin)

# View service metrics
curl http://localhost:8000/metrics | head -20  # FastAPI
curl http://localhost:5001/metrics | head -20  # ML service
curl http://localhost:8080/metrics | head -20  # vLLM
```

---

## Emergency Recovery

### Service crashed / won't restart

```bash
# Check logs for error
docker compose logs backend --tail 50

# Rebuild image (slow but sometimes fixes environment issues)
docker compose build --no-cache backend
docker compose up -d backend

# If that fails, check if a DB migration is needed
docker compose logs postgres | grep -i "migration\|error"
```

### Database corruption / won't start

```bash
# Check postgres logs
docker compose logs postgres

# Try restart
docker compose restart postgres

# If still fails, last resort (DESTROYS DATA):
docker compose down -v postgres
docker compose up -d postgres
# You'll need to restore from backup
```

### vLLM OOM (runs out of GPU memory)

```bash
# Check GPU memory
nvidia-smi

# Reduce memory utilization in .env
# Current: VLLM_GPU_MEMORY_UTILIZATION=0.85
# Change to: VLLM_GPU_MEMORY_UTILIZATION=0.75

# Redeploy
docker compose build vllm
docker compose up -d vllm
```

### All services down / won't start

```bash
# Check Docker
docker info

# Restart Docker daemon
sudo systemctl restart docker

# Then try again
docker compose up -d

# Check if ports are in use
lsof -i :80
lsof -i :443
lsof -i :8000
```

---

## Scaling (Future)

Currently: 1× instance with 2× L40S + all services on one host.

For multi-instance scaling, see `DEPLOYMENT.md` (Kubernetes section).

---

## Environment Changes

```bash
# Update .env (e.g., change GROQ_API_KEY)
nano /opt/lipi/.env

# Apply changes (no downtime if only env vars)
docker compose up -d backend

# Check it took effect
docker compose logs backend | grep "GROQ_API_KEY"
```

---

## Useful Aliases

Add to `~/.bashrc` on the server:

```bash
alias lipi-logs='cd /opt/lipi && make logs'
alias lipi-health='cd /opt/lipi && make server-health'
alias lipi-ps='docker compose ps'
alias lipi-shell='docker compose exec postgres psql -U lipi -d lipi'
```

Then restart shell or `. ~/.bashrc`.

---

## Further Reading

- **Deployment**: `DEPLOYMENT_QUICK_START.md`
- **Architecture**: `DEV_ONBOARDING.md`, section 6
- **Database Schema**: `DATABASE_SCHEMA.md`
- **Gamification**: `GAMIFICATION_DATA_MODEL.md`
- **Troubleshooting**: `DEPLOYMENT_QUICK_START.md`, "Troubleshooting" section
