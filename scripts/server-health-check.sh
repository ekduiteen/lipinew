#!/usr/bin/env bash
# =============================================================================
# LIPI — Server health check
# Run on the server to diagnose any issues:
#   bash /opt/lipi/scripts/server-health-check.sh
# =============================================================================

set -u
DEPLOY_DIR="/opt/lipi"
COMPOSE="docker compose -f $DEPLOY_DIR/docker-compose.yml"

echo "=== LIPI Server Health Check ==="
echo ""

# ─── System info ────────────────────────────────────────────────────────────
echo "[SYSTEM]"
echo "Hostname: $(hostname)"
echo "Kernel: $(uname -r)"
echo "Uptime: $(uptime -p)"
echo ""

# ─── GPU check ──────────────────────────────────────────────────────────────
echo "[GPU]"
if command -v nvidia-smi &>/dev/null; then
    GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
    echo "GPUs: $GPU_COUNT"
    nvidia-smi --query-gpu=name,memory.total,temperature.gpu --format=csv,noheader
else
    echo "ERROR: nvidia-smi not found"
fi
echo ""

# ─── Docker check ────────────────────────────────────────────────────────────
echo "[DOCKER]"
if docker info &>/dev/null; then
    echo "Docker: $(docker --version)"
    echo "Containers running: $(docker ps -q | wc -l)"
    echo "Total containers: $(docker ps -a -q | wc -l)"

    # Check nvidia runtime
    if docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi --list-gpus 2>/dev/null | grep -q "GPU"; then
        echo "GPU passthrough: OK"
    else
        echo "GPU passthrough: FAILED"
    fi
else
    echo "ERROR: Docker is not running"
fi
echo ""

# ─── Container status ────────────────────────────────────────────────────────
echo "[CONTAINERS]"
$COMPOSE ps --format "table {{.Names}}\t{{.Status}}" || true
echo ""

# ─── Service health (HTTP) ──────────────────────────────────────────────────
echo "[SERVICE HEALTH]"

_check_http() {
    local url="$1"
    local name="$2"
    if curl -sf "$url" -o /dev/null 2>/dev/null; then
        echo "  ✓ $name"
        return 0
    else
        echo "  ✗ $name (unreachable at $url)"
        return 1
    fi
}

_check_http "http://localhost:8000/health" "Backend (FastAPI)"
_check_http "http://localhost:5001/health" "ML Service (STT+TTS)"
_check_http "http://localhost:8080/v1/models" "vLLM (LLM inference)"
echo ""

# ─── Database check ─────────────────────────────────────────────────────────
echo "[DATABASE]"
if $COMPOSE exec -T postgres pg_isready -U lipi -d lipi &>/dev/null; then
    TABLES=$($COMPOSE exec -T postgres psql -U lipi -d lipi -tc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "?")
    echo "  ✓ PostgreSQL (tables: $TABLES)"
else
    echo "  ✗ PostgreSQL (not responding)"
fi
echo ""

# ─── Cache check ────────────────────────────────────────────────────────────
echo "[CACHE]"
if $COMPOSE exec -T valkey valkey-cli ping &>/dev/null; then
    KEYS=$($COMPOSE exec -T valkey valkey-cli DBSIZE 2>/dev/null | grep keys || echo "?")
    echo "  ✓ Valkey ($KEYS)"
else
    echo "  ✗ Valkey (not responding)"
fi
echo ""

# ─── Storage check ──────────────────────────────────────────────────────────
echo "[STORAGE]"
if $COMPOSE exec -T minio mc admin info lipi &>/dev/null 2>&1; then
    echo "  ✓ MinIO"
else
    echo "  ✗ MinIO (not responding)"
fi
echo ""

# ─── Disk usage ──────────────────────────────────────────────────────────────
echo "[DISK USAGE]"
df -h / | tail -1 | awk '{print "  Root: " $5 " used (" $4 " free)"}'
docker system df | tail -4 || true
echo ""

# ─── Network check ──────────────────────────────────────────────────────────
echo "[NETWORK]"
if command -v ss &>/dev/null; then
    OPEN_PORTS=$(ss -tlnp 2>/dev/null | grep LISTEN | wc -l)
    echo "  Listening ports: $OPEN_PORTS"
    echo "  Port 80 (HTTP):"
    ss -tlnp 2>/dev/null | grep ":80 " | sed 's/^/    /'
    echo "  Port 443 (HTTPS):"
    ss -tlnp 2>/dev/null | grep ":443 " | sed 's/^/    /'
fi
echo ""

# ─── Firewall check ─────────────────────────────────────────────────────────
echo "[FIREWALL]"
if command -v ufw &>/dev/null; then
    if ufw status | grep -q "Status: active"; then
        echo "  ✓ UFW enabled"
        ufw status | grep -E "^[0-9]|^To " | head -10 | sed 's/^/    /'
    else
        echo "  ⚠ UFW inactive"
    fi
fi
echo ""

# ─── Certificate check (Caddy) ──────────────────────────────────────────────
echo "[CERTIFICATES]"
CADDY_DATA="/var/lib/docker/volumes/lipi_caddy_data/_data"
if [ -d "$CADDY_DATA" ]; then
    CERT_COUNT=$(find "$CADDY_DATA" -name "*.crt" 2>/dev/null | wc -l)
    echo "  Certificates stored: $CERT_COUNT"
    NEWEST=$(find "$CADDY_DATA" -name "*.crt" -type f -exec ls -t {} + 2>/dev/null | head -1 | xargs stat -c %y 2>/dev/null || echo "unknown")
    echo "  Newest cert: $NEWEST"
else
    echo "  (Caddy data not found)"
fi
echo ""

# ─── Logs check ──────────────────────────────────────────────────────────────
echo "[RECENT ERRORS]"
echo "Backend errors (last 5):"
$COMPOSE logs backend 2>/dev/null | grep -i error | tail -5 | sed 's/^/  /' || echo "  (none)"
echo ""
echo "vLLM errors (last 5):"
$COMPOSE logs vllm 2>/dev/null | grep -i error | tail -5 | sed 's/^/  /' || echo "  (none)"
echo ""

# ─── Quick connectivity test ────────────────────────────────────────────────
echo "[CONNECTIVITY]"
if curl -sf https://www.google.com -o /dev/null 2>/dev/null; then
    echo "  ✓ Internet: OK"
else
    echo "  ✗ Internet: No connectivity"
fi
echo ""

# ─── Summary ────────────────────────────────────────────────────────────────
echo "[SUMMARY]"
HEALTHY=0
TOTAL=0
$COMPOSE ps --format json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
healthy = sum(1 for x in data if 'healthy' in x.get('State', '').lower() or 'running' in x.get('State', '').lower())
total = len(data)
print(f'  Running: {healthy}/{total} containers')
" || echo "  (Unable to parse container status)"

echo ""
echo "=== End of health check ==="
