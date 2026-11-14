#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8001 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT INT TERM
cd regionDashboard
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
