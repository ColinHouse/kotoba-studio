#!/usr/bin/env bash
# Run the API server (auto-reload) and the Vite dev server together.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export KOTOBA_DATA_DIR="${KOTOBA_DATA_DIR:-$ROOT/data}"

(cd "$ROOT/backend" && uv run uvicorn kotoba.app:app --factory --reload --host 127.0.0.1 --port 8720) &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

(cd "$ROOT/frontend" && npm run dev)
