#!/usr/bin/env bash
# Run SentinelOps backend + frontend for local development (macOS / Linux / Git Bash).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting backend on :8000 ..."
# Prefer the POSIX venv layout (macOS / Linux), fall back to the Windows layout
# (Git Bash). Errors are NOT suppressed so backend startup failures are visible.
if [ -x "$ROOT/backend/.venv/bin/python" ]; then
    PYTHON="$ROOT/backend/.venv/bin/python"
elif [ -x "$ROOT/backend/.venv/Scripts/python.exe" ]; then
    PYTHON="$ROOT/backend/.venv/Scripts/python.exe"
else
    echo "No virtualenv found at backend/.venv. Create it first (python -m venv .venv)." >&2
    exit 1
fi
( cd "$ROOT/backend" && "$PYTHON" -m uvicorn app.main:app --reload --port 8000 ) &
BACKEND=$!

echo "Starting frontend on :5173 ..."
( cd "$ROOT/frontend" && npm run dev ) &
FRONTEND=$!

trap 'kill $BACKEND $FRONTEND 2>/dev/null || true' EXIT
echo "SentinelOps running. Ctrl+C to stop."
wait
