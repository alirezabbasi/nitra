#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0052] FAIL: $1" >&2
  exit 1
}

echo "[dev-0052] checking reconciliation/runbook evidence capture for live adapter behavior..."

[[ -f infra/timescaledb/init/018_control_panel_reconciliation_evidence.sql ]] || fail "missing migration 018_control_panel_reconciliation_evidence.sql"
rg -n 'CREATE TABLE IF NOT EXISTS control_panel_reconciliation_evidence' infra/timescaledb/init/018_control_panel_reconciliation_evidence.sql >/dev/null || fail "migration missing reconciliation evidence table"

rg -n 'capture_runbook_reconciliation_evidence' services/charting/app.py >/dev/null || fail "missing runbook reconciliation evidence capture helper"
rg -n 'control_panel_reconciliation_evidence' services/charting/app.py >/dev/null || fail "missing evidence table usage"
rg -n 'order_id|correlation_id|lookback_minutes|evidence_summary' services/charting/app.py >/dev/null || fail "missing runbook evidence payload fields"

echo "[dev-0052] PASS"
