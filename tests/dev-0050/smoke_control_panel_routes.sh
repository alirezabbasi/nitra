#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0050:routes] FAIL: $1" >&2
  exit 1
}

check_pattern() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  rg -n "$pattern" "$file" >/dev/null || fail "missing route pattern: $label"
}

check_pattern services/control-panel/app/api/routers/health.py '@router\.get\("/health"\)' 'GET /health'
check_pattern services/control-panel/app/main.py '@app\.get\("/control-panel"\)' 'GET /control-panel'
check_pattern services/control-panel/app/api/routers/overview.py '@router\.get\("/api/v1/control-panel/overview"\)' 'GET /api/v1/control-panel/overview'
check_pattern services/control-panel/app/api/routers/charting.py '@router\.get\("/api/v1/control-panel/charting/profile"\)' 'GET /api/v1/control-panel/charting/profile'
check_pattern services/control-panel/app/api/routers/charting.py '@router\.get\("/api/v1/charting/bars/history"\)' 'GET /api/v1/charting/bars/history'
check_pattern services/control-panel/app/api/routers/charting.py '@router\.get\("/api/v1/bars/history"\)' 'GET /api/v1/bars/history'
check_pattern services/control-panel/app/api/routers/charting.py '@router\.post\("/api/v1/backfill/window"\)' 'POST /api/v1/backfill/window'
check_pattern services/control-panel/app/api/routers/charting.py '@router\.get\("/api/v1/coverage/status"\)' 'GET /api/v1/coverage/status'

echo "ROUTE_SMOKE_OK"
