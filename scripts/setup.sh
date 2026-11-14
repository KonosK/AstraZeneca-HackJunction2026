#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.12 -m venv .venv
PIP_CACHE_DIR=/workspace/.cache/pip .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
cd regionDashboard
npm ci --cache /workspace/.cache/npm --no-audit --no-fund
npm run build
