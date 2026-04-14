#!/bin/bash
# Copy LIPI to remote server /data/lipi
# Usage: bash copy_to_remote.sh

REMOTE_USER="ekduiteen"
REMOTE_HOST="202.51.2.50"
REMOTE_PORT="41447"
REMOTE_PATH="/data/lipi"

echo "=========================================="
echo "Copying LIPI to remote server"
echo "=========================================="
echo ""

if [ ! -f "docker-compose.yml" ]; then
    echo "ERROR: Run this from the LIPI root directory"
    exit 1
fi

echo "Copying to: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"
echo ""

# Copy all necessary files and directories
files_to_copy=(
    "backend"
    "frontend"
    "ml"
    "docker-compose.yml"
    "Caddyfile"
    "init-db.sql"
    "scripts"
    "monitoring"
    "Makefile"
    ".env.example"
)

for file in "${files_to_copy[@]}"; do
    if [ -e "$file" ]; then
        echo "▶ Copying: $file"
        scp -P "$REMOTE_PORT" -r "$file" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/" 2>&1 | grep -E "error|Error" || echo "  ✓ Done"
    else
        echo "⊘ Skipping: $file (not found)"
    fi
done

echo ""
echo "=========================================="
echo "Copy complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. SSH to remote: ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"
echo "2. Check files: cd /data/lipi && ls -la"
echo "3. Start services: docker compose up -d backend frontend"
echo "4. From local machine, SSH tunnel:"
echo "   ssh -p $REMOTE_PORT -L 8000:localhost:8000 -L 3000:localhost:3000 -L 8100:localhost:8100 -L 5001:localhost:5001 $REMOTE_USER@$REMOTE_HOST"
echo "5. Visit: http://localhost:3000"
echo ""
