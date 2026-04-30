#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0063] FAIL: $1" >&2
  exit 1
}

echo "[dev-0063] checking post-cutover observability revalidation contract..."

[[ -f docs/development/tickets/DEV-00063-control-panel-post-cutover-observability-revalidation.md ]] || fail "missing DEV-00063 ticket"
[[ -x scripts/observability/control_panel_cutover_sustained_check.sh ]] || fail "missing sustained-check script"

rg -n 'Success ratio|5xx|p95 latency|/api/v1/control-panel/migration/status|/api/v1/charting/markets/available' docs/design/ingestion/06-devops/control-panel-rollout-cutover-runbook.md >/dev/null || fail "runbook missing sustained-load threshold contract"
rg -n 'make test-dev-0063|control_panel_cutover_sustained_check.sh' docs/design/ingestion/06-devops/control-panel-rollout-cutover-runbook.md >/dev/null || fail "runbook missing validation command wiring"

# Script contract assertions
rg -n 'DURATION_SECS|BASE_URL|OUTPUT_PATH|control-panel-observability-revalidation' scripts/observability/control_panel_cutover_sustained_check.sh >/dev/null || fail "sustained-check script missing core controls"

# Fast static validation only; live run is optional and environment-dependent.
if [[ "${DEV0063_LIVE:-0}" == "1" ]]; then
  scripts/observability/control_panel_cutover_sustained_check.sh >/dev/null
fi

echo "[dev-0063] PASS"
