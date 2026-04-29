#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0042] FAIL: $1" >&2
  exit 1
}

echo "[dev-0042] checking portfolio reconciliation wiring..."
[[ -f infra/timescaledb/init/016_portfolio_reconciliation_log.sql ]] || fail "missing migration 016_portfolio_reconciliation_log.sql"
rg -n 'reconcile_account_state|persist_reconciliation_result|portfolio_reconciliation_drift' services/portfolio-engine/src/main.rs >/dev/null || fail "missing reconciliation runtime hooks"
rg -n 'PORTFOLIO_MAX_GROSS_EXPOSURE_NOTIONAL|PORTFOLIO_MAX_ABS_NET_EXPOSURE_NOTIONAL|PORTFOLIO_MIN_EQUITY|PORTFOLIO_DRIFT_TOPIC' services/portfolio-engine/src/main.rs >/dev/null || fail "missing invariant env controls"
rg -n 'PORTFOLIO_DRIFT_TOPIC' docker-compose.yml >/dev/null || fail "missing drift topic compose wiring"

echo "[dev-0042] running portfolio regression tests..."
CARGO_TARGET_DIR=/tmp/nitra-portfolio-engine-target cargo test --manifest-path services/portfolio-engine/Cargo.toml parse_fill_payload
CARGO_TARGET_DIR=/tmp/nitra-portfolio-engine-target cargo test --manifest-path services/portfolio-engine/Cargo.toml reconciliation_detects_drift_reasons

echo "[dev-0042] PASS"
