#!/usr/bin/env bash
# =============================================================================
# LIPI — Production deploy / update script
# Run on the server as the deploy user (lipi) or root:
#   bash /opt/lipi/scripts/deploy.sh
#
# What this does:
#   1. Pull latest code from git
#   2. Build Docker images
#   3. Start / recreate services (zero-downtime for stateless services)
#   4. Wait for all health checks to pass
#   5. Print final status
# =============================================================================

set -euo pipefail
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="docker compose -f $DEPLOY_DIR/docker-compose.yml"
LOG="$DEPLOY_DIR/deploy.log"

exec > >(tee -a "$LOG") 2>&1
echo "=== Deploy started at $(date) ==="
echo "Working dir: $DEPLOY_DIR"

cd "$DEPLOY_DIR"

# ─── Pre-flight checks ────────────────────────────────────────────────────────
echo ""
echo "[preflight] Checking requirements..."

if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Copy .env.example and fill in values."
    exit 1
fi

# Warn if any critical placeholders are still in .env
UNFILLED=$(grep -E "change_me|YOUR_|<[A-Z_]+>" .env | grep -v "^#" || true)
if [ -n "$UNFILLED" ]; then
    echo "WARNING: Unfilled placeholders in .env:"
    echo "$UNFILLED"
    echo ""
fi

docker info &>/dev/null || { echo "ERROR: Docker is not running"; exit 1; }

# Verify GPU access
GPU_COUNT=$(nvidia-smi --list-gpus 2>/dev/null | wc -l || echo 0)
echo "GPUs visible: $GPU_COUNT"
if [ "$GPU_COUNT" -lt 2 ]; then
    echo "WARNING: Expected 2× L40S. vLLM and ML service require GPUs."
fi

# ─── Pull latest code ────────────────────────────────────────────────────────
echo ""
echo "[1/4] Pulling latest code..."
git fetch origin
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "unknown")
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "Already up to date: $LOCAL"
else
    git pull --ff-only
    echo "Updated to: $(git rev-parse HEAD)"
fi

# ─── Build images ─────────────────────────────────────────────────────────────
echo ""
echo "[2/4] Building Docker images..."
$COMPOSE build --pull backend frontend ml
echo "Build complete."

# ─── Start services ──────────────────────────────────────────────────────────
echo ""
echo "[3/4] Starting services..."

# Infra first (postgres, valkey, minio)
echo "  Starting infra..."
$COMPOSE up -d postgres valkey minio
echo "  Waiting for infra health checks..."
_wait_healthy() {
    local svc="$1"
    local max=60
    local i=0
    while [ $i -lt $max ]; do
        STATUS=$($COMPOSE ps --format json "$svc" 2>/dev/null \
            | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")
        if [ "$STATUS" = "healthy" ]; then
            echo "    $svc: healthy"
            return 0
        fi
        sleep 2
        i=$((i+2))
    done
    echo "    WARNING: $svc did not become healthy within ${max}s"
    return 1
}
_wait_healthy postgres || true
_wait_healthy valkey   || true
_wait_healthy minio    || true

# MinIO bucket init
$COMPOSE up -d minio-init

# App services
echo "  Starting app services (backend, frontend, caddy)..."
$COMPOSE up -d backend frontend caddy

# GPU services (slow cold start — vLLM takes ~5 min)
echo "  Starting GPU services (ml, vllm)..."
echo "  NOTE: vLLM cold start takes ~5 min. Groq fallback is active until then."
$COMPOSE up -d ml vllm

# ─── Health check loop ────────────────────────────────────────────────────────
echo ""
echo "[4/4] Waiting for health checks..."

_http_health() {
    local url="$1"
    local name="$2"
    local max="${3:-120}"
    local i=0
    while [ $i -lt $max ]; do
        if curl -sf "$url" -o /dev/null 2>/dev/null; then
            echo "    $name: UP"
            return 0
        fi
        sleep 5
        i=$((i+5))
    done
    echo "    WARNING: $name not responding after ${max}s"
    return 1
}

_http_health "http://localhost:8000/health" "backend (FastAPI)" 60 || true
_http_health "http://localhost:5001/health" "ml service (STT+TTS)" 180 || true
# vLLM gets a long timeout — model loading takes time
_http_health "http://localhost:8080/v1/models" "vLLM (Qwen3-32B)" 600 || \
    echo "    vLLM still loading — will come online. Check: docker compose logs vllm"

# ─── Final status ─────────────────────────────────────────────────────────────
echo ""
echo "=== Container status ==="
$COMPOSE ps

echo ""
echo "=== Backend health ==="
curl -s http://localhost:8000/health 2>/dev/null | python3 -m json.tool 2>/dev/null || \
    echo "(backend not yet reachable)"

echo ""
echo "=== Deploy complete at $(date) ==="
echo ""
echo "Useful commands:"
echo "  View all logs:    docker compose logs -f"
echo "  Backend logs:     docker compose logs -f backend"
echo "  vLLM progress:    docker compose logs -f vllm"
echo "  ML service logs:  docker compose logs -f ml"
echo "  Stop all:         docker compose down"
echo "  Monitoring:       docker compose --profile monitoring up -d"
