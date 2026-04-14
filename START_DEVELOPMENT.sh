#!/bin/bash

# LIPI Development Startup Script
# This script starts everything you need to develop LIPI

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          LIPI Development Environment Startup              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the LIPI root directory"
    echo "   (where you see backend/, frontend/, and ml/ folders)"
    exit 1
fi

# Kill any existing processes on ports we need
cleanup_ports() {
    for port in 8000 3000; do
        if lsof -i :$port >/dev/null 2>&1; then
            echo "⚠️  Found process on port $port, cleaning up..."
            lsof -ti :$port | xargs kill -9 2>/dev/null || true
        fi
    done
}

echo "🔧 Preparing environment..."
cleanup_ports

echo ""
echo "📌 You now need 3 terminals:"
echo ""
echo "Terminal 1: Run this command (keep it running):"
echo "─────────────────────────────────────────────────────"
echo "ssh -p 41447 -L 8000:localhost:8000 -L 8080:localhost:8080 -L 5001:localhost:5001 -L 5432:localhost:5432 -L 6379:localhost:6379 ekduiteen@202.51.2.50"
echo "─────────────────────────────────────────────────────"
echo ""
echo "Terminal 2: Run the backend"
echo "─────────────────────────────────────────────────────"
cd backend
echo "cd backend"
echo "export DATABASE_URL='postgresql+asyncpg://lipi:lipi_secure_password_change_me_in_prod@localhost:5432/lipi'"
echo "export VALKEY_URL='valkey://localhost:6379/0'"
echo "export VLLM_URL='http://localhost:8080'"
echo "export VLLM_MODEL='lipi'"
echo "export ML_SERVICE_URL='http://localhost:5001'"
echo "export MINIO_ENDPOINT='localhost:9000'"
echo "export MINIO_ACCESS_KEY='lipiuser'"
echo "export MINIO_SECRET_KEY='lipipassword_change_me'"
echo "export JWT_SECRET='fab2865c45f73e8a546747c7563f897d94c0a3675a4c061da0d760d158699ba7'"
echo "export GOOGLE_CLIENT_ID='your_google_client_id'"
echo "export GOOGLE_CLIENT_SECRET='your_google_client_secret'"
echo "export LOG_LEVEL='DEBUG'"
echo "pip install -r requirements.txt"
echo "uvicorn main:app --reload --port 8000 --host 0.0.0.0"
echo "─────────────────────────────────────────────────────"
echo ""
echo "Terminal 3: Run the frontend"
echo "─────────────────────────────────────────────────────"
cd ../frontend
echo "cd frontend"
echo "export NEXT_PUBLIC_API_URL='http://localhost:8000'"
echo "export NEXT_PUBLIC_WS_URL='ws://localhost:8000'"
echo "npm install  # only if first time"
echo "npm run dev"
echo "─────────────────────────────────────────────────────"
echo ""
echo "🌐 Then open your browser:"
echo "   http://localhost:3000"
echo ""
echo "✨ All set! Your LIPI backend & infrastructure are running on:"
echo "   Remote Server: 202.51.2.50:41447 /data/lipi"
echo ""
echo "📊 What's Running Remotely:"
echo "   ✅ PostgreSQL (5432)"
echo "   ✅ Valkey Cache (6379)"
echo "   ✅ MinIO (9000/9001)"
echo "   ✅ vLLM + Qwen2.5-AWQ (8080)"
echo "   ✅ ML Service STT/TTS (5001) - warming up"
echo "   ✅ FastAPI Backend (8000)"
echo ""
echo "💡 Pro Tips:"
echo "   - Backend auto-reloads on code changes (uvicorn --reload)"
echo "   - Frontend hot-reloads (Next.js dev server)"
echo "   - SSH tunnel must stay open in Terminal 1"
echo "   - Check logs with: docker logs -f lipi-<service> (on remote)"
echo ""
echo "🆘 Troubleshooting:"
echo "   Can't connect? Check SSH tunnel is running"
echo "   Port in use? Run: lsof -i :8000 or :3000, then kill -9 <PID>"
echo "   Backend can't reach remote? Verify SSH tunnel has all -L flags"
echo ""
echo "📚 Documentation:"
echo "   - REMOTE_SETUP_READY.md (complete guide)"
echo "   - SETUP_QUICK_REFERENCE.txt (commands & credentials)"
echo ""
echo "Happy coding! 🚀"
echo ""
