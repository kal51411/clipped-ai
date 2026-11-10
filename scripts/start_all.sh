#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Start Redis if not already running
if ! redis-cli ping >/dev/null 2>&1; then
    echo "Starting Redis..."
    redis-server --daemonize yes || true
fi

echo "=================================================="
echo " Starting Clipped-AI Full Stack Platform"
echo " Backend:  http://127.0.0.1:8000"
echo " Frontend: http://localhost:3000"
echo "=================================================="

# Start backend in background
bash "$ROOT_DIR/scripts/start_backend.sh" &
BACKEND_PID=$!

# Start Celery worker in background
bash "$ROOT_DIR/scripts/start_worker.sh" &
WORKER_PID=$!

# Trap Ctrl+C to kill child background processes cleanly
cleanup() {
    echo ""
    echo "Stopping all services..."
    kill "$BACKEND_PID" "$WORKER_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start Next.js frontend in foreground
cd "$ROOT_DIR/frontend"
npm run dev
