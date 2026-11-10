#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if [ -f "$BACKEND_DIR/venv/bin/activate" ]; then
    source "$BACKEND_DIR/venv/bin/activate"
fi

cd "$BACKEND_DIR"
echo "Starting Clipped-AI FastAPI Backend on http://127.0.0.1:8000..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
