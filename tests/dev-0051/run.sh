#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0051] FAIL: $1" >&2
  exit 1
}

echo "[dev-0051] checking rollout cutover and deprecation closure..."

# Post-cutover state should expose native compatibility mode.
rg -n 'native-charting-cutover|legacy_charting_aliases' services/control-panel/app/api/routers/health.py >/dev/null || fail "missing cutover status config"
rg -n '@router\.get\("/api/v1/control-panel/migration/status"\)' services/control-panel/app/api/routers/health.py >/dev/null || fail "missing migration status endpoint"

# Legacy compatibility alias routes must be retired.
if rg -n '/api/v1/bars/hot|/api/v1/bars/history|/api/v1/ticks/hot|/api/v1/markets/available|/api/v1/venues|/api/v1/backfill/window|/api/v1/coverage/status' services/control-panel/app/api/routers/charting.py >/dev/null; then
  fail "legacy charting alias routes still present"
fi

# Rollout/deprecation docs must exist.
[[ -f docs/design/ingestion/06-devops/control-panel-rollout-cutover-runbook.md ]] || fail "missing rollout runbook"
[[ -f docs/design/ingestion/06-devops/control-panel-deprecation-closure-report.md ]] || fail "missing deprecation closure report"
rg -n 'shadow validation|primary switch|rollback|deprecation' docs/design/ingestion/06-devops/control-panel-rollout-cutover-runbook.md >/dev/null || fail "rollout runbook missing required sections"
rg -n 'retired routes|acceptance window|closure date' docs/design/ingestion/06-devops/control-panel-deprecation-closure-report.md >/dev/null || fail "deprecation report missing closure evidence fields"

# Existing quality gates must still pass after cutover.
tests/dev-0050/run.sh

echo "[dev-0051] PASS"
