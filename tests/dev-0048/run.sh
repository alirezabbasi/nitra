#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0048] FAIL: $1" >&2
  exit 1
}

echo "[dev-0048] checking control-panel charting extraction + compatibility bridge..."

[[ -f services/control-panel/app/api/routers/charting.py ]] || fail "missing charting router"
[[ -f services/control-panel/app/services/charting/legacy_proxy.py ]] || fail "missing charting proxy service"

rg -n 'include_router\(charting_router\)' services/control-panel/app/main.py >/dev/null || fail "main.py missing charting router inclusion"
rg -n '/api/v1/charting/bars/hot|/api/v1/charting/bars/history|/api/v1/charting/ticks/hot|/api/v1/charting/markets/available|/api/v1/charting/venues|/api/v1/charting/backfill/window|/api/v1/charting/coverage/status|/api/v1/control-panel/charting/profile' services/control-panel/app/api/routers/charting.py >/dev/null || fail "missing extracted charting routes"
rg -n '/api/v1/bars/hot|/api/v1/bars/history|/api/v1/ticks/hot|/api/v1/markets/available|/api/v1/venues|/api/v1/backfill/window|/api/v1/coverage/status' services/control-panel/app/api/routers/charting.py >/dev/null || fail "missing legacy compatibility routes"
rg -n 'Deprecation|Sunset|successor-version' services/control-panel/app/services/charting/legacy_proxy.py >/dev/null || fail "missing deprecation compatibility headers"

python -m py_compile \
  services/control-panel/app/main.py \
  services/control-panel/app/core/legacy_bridge.py \
  services/control-panel/app/services/control_panel/legacy_proxy.py \
  services/control-panel/app/services/charting/legacy_proxy.py \
  services/control-panel/app/api/routers/charting.py

echo "[dev-0048] PASS"
