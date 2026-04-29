#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0053] FAIL: $1" >&2
  exit 1
}

echo "[dev-0053] checking ingestion KPI monitor coverage/tick page..."

rg -n '@app\.get\("/api/v1/control-panel/ingestion/kpi"\)' services/charting/app.py >/dev/null || fail "missing ingestion KPI endpoint"
rg -n 'target_1m_bars|tick_sla_seconds|meets_both_kpi|raw_tick|ohlcv_bar' services/charting/app.py >/dev/null || fail "missing KPI aggregation fields"
rg -n 'data-section="kpi"|workspace-kpi|kpiMetrics|kpiTable' services/control-panel/frontend/src/control-panel.html >/dev/null || fail "missing KPI workspace in frontend"
rg -n 'loadIngestionKpi|/api/v1/control-panel/ingestion/kpi|kpiLoadBtn' services/control-panel/frontend/src/app/control-panel.js >/dev/null || fail "missing KPI frontend loader wiring"
rg -n '@router\.get\("/api/v1/control-panel/ingestion/kpi"\)' services/control-panel/app/api/routers/ingestion.py >/dev/null || fail "missing proxy route for KPI endpoint"

echo "[dev-0053] PASS"
