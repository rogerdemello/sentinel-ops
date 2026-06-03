#!/usr/bin/env bash
# Run SentinelOps backend + frontend for local development (macOS / Linux / Git Bash).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting backend on :8000 ..."
( cd "$ROOT/backend" && ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000 \
    2>/dev/null || ./.venv/bin/python -m uvicorn app.main:app --reload --port 8000 ) &
BACKEND=$!

echo "Starting frontend on :5173 ..."
( cd "$ROOT/frontend" && npm run dev ) &
FRONTEND=$!

trap 'kill $BACKEND $FRONTEND 2>/dev/null || true' EXIT
echo "SentinelOps running. Ctrl+C to stop."
wait
