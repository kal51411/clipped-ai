#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if [ -f "$BACKEND_DIR/venv/bin/activate" ]; then
    source "$BACKEND_DIR/venv/bin/activate"
fi

cd "$BACKEND_DIR"
echo "Starting Clipped-AI Celery Worker on queues [celery,video,ai]..."
exec celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 -Q celery,video,ai
