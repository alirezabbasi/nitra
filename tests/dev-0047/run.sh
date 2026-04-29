#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0047] FAIL: $1" >&2
  exit 1
}

echo "[dev-0047] checking domain router split + service extraction..."
for f in \
  services/control-panel/app/api/routers/auth_session.py \
  services/control-panel/app/api/routers/overview.py \
  services/control-panel/app/api/routers/ingestion.py \
  services/control-panel/app/api/routers/risk_portfolio.py \
  services/control-panel/app/api/routers/execution.py \
  services/control-panel/app/api/routers/ops.py \
  services/control-panel/app/api/routers/research.py \
  services/control-panel/app/api/routers/config.py \
  services/control-panel/app/api/routers/search.py; do
  [[ -f "$f" ]] || fail "missing router: $f"
done

[[ -f services/control-panel/app/services/control_panel/legacy_proxy.py ]] || fail "missing service-layer proxy"
rg -n 'include_router\(auth_session_router\)|include_router\(overview_router\)|include_router\(ingestion_router\)|include_router\(risk_portfolio_router\)|include_router\(execution_router\)|include_router\(ops_router\)|include_router\(research_router\)|include_router\(config_router\)|include_router\(search_router\)' services/control-panel/app/main.py >/dev/null || fail "main.py missing router composition"

if rg -n 'SELECT |INSERT |UPDATE |DELETE |FROM ' services/control-panel/app/api/routers/*.py >/dev/null; then
  fail "router files contain inline SQL"
fi

python -m py_compile \
  services/control-panel/app/main.py \
  services/control-panel/app/core/legacy_bridge.py \
  services/control-panel/app/services/control_panel/legacy_proxy.py \
  services/control-panel/app/api/routers/*.py

echo "[dev-0047] PASS"
