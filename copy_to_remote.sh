#!/bin/bash
# Sync committed LIPI source to the remote snapshot at /data/lipi.
# Usage: bash copy_to_remote.sh

set -euo pipefail

REMOTE_USER="ekduiteen"
REMOTE_HOST="202.51.2.50"
REMOTE_PORT="41447"
REMOTE_PATH="/data/lipi"

echo "=========================================="
echo "Syncing committed LIPI source to remote"
echo "=========================================="
echo ""

if [ ! -d ".git" ]; then
    echo "ERROR: Run this from the git repo root"
    exit 1
fi

echo "Remote target: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"
echo "Commit: $(git rev-parse --short HEAD)"
echo ""
echo "This script syncs the committed tree from HEAD."
echo "It does not copy uncommitted local changes."
echo ""

git archive --format=tar HEAD \
    backend \
    ml \
    scripts \
    init-db.sql \
    .env.example \
    Caddyfile \
| ssh -p "$REMOTE_PORT" "$REMOTE_USER@$REMOTE_HOST" "mkdir -p '$REMOTE_PATH' && tar -xf - -C '$REMOTE_PATH'"

echo ""
echo "=========================================="
echo "Sync complete"
echo "=========================================="
echo ""
echo "Next steps on remote:"
echo "  ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"
echo "  cd $REMOTE_PATH"
echo "  docker compose -f docker-compose.lipi.yml up -d --build backend"
echo "  curl http://127.0.0.1:8000/health"
echo "  curl http://127.0.0.1:5001/health"
echo "  curl http://127.0.0.1:8210/v1/models"
echo ""
echo "If the remote compose file changed, update docker-compose.lipi.yml separately."
