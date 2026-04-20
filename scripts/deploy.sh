#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="/data/lipi"
COMPOSE="docker compose -f $DEPLOY_DIR/docker-compose.lipi.yml"
LOG="$DEPLOY_DIR/deploy.log"

exec > >(tee -a "$LOG") 2>&1
echo "=== Deploy started at $(date) ==="
echo "Working dir: $DEPLOY_DIR"

cd "$DEPLOY_DIR"

echo "[1/4] Preflight"
docker info >/dev/null
test -f docker-compose.lipi.yml

echo "[2/4] Starting infra"
$COMPOSE up -d postgres valkey minio
$COMPOSE up -d ml

echo "[3/4] Rebuilding backend"
$COMPOSE up -d --build backend

echo "[4/4] Health checks"
curl -fsS http://127.0.0.1:5001/health >/dev/null
curl -fsS http://127.0.0.1:8210/v1/models >/dev/null
curl -fsS http://127.0.0.1:8000/health >/dev/null

echo ""
echo "=== Container status ==="
$COMPOSE ps
echo ""
echo "=== Backend health ==="
curl -sS http://127.0.0.1:8000/health
echo ""
echo "=== Deploy complete at $(date) ==="
