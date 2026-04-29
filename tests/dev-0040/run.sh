#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0040] FAIL: $1" >&2
  exit 1
}

echo "[dev-0040] checking risk trace schema and runtime wiring..."
[[ -f infra/timescaledb/init/015_risk_policy_trace.sql ]] || fail "missing migration 015_risk_policy_trace.sql"
rg -n 'policy_hits|evaluation_trace' services/risk-engine/src/main.rs >/dev/null || fail "missing policy trace fields in risk runtime"
rg -n 'RISK_POLICY_BUNDLE_ID|RISK_MAX_REGIME_VOLATILITY|RISK_MAX_CONFLICT_SCORE|RISK_KILL_SWITCH_MODE' services/risk-engine/src/main.rs >/dev/null || fail "missing expanded risk policy envs"

echo "[dev-0040] running risk policy regression/stress suite..."
CARGO_TARGET_DIR=/tmp/nitra-risk-engine-target cargo test --manifest-path services/risk-engine/Cargo.toml risk_policy_evaluation_is_deterministic
CARGO_TARGET_DIR=/tmp/nitra-risk-engine-target cargo test --manifest-path services/risk-engine/Cargo.toml rejects_when_regime_volatility_exceeded
CARGO_TARGET_DIR=/tmp/nitra-risk-engine-target cargo test --manifest-path services/risk-engine/Cargo.toml carries_policy_trace_metadata
CARGO_TARGET_DIR=/tmp/nitra-risk-engine-target cargo test --manifest-path services/risk-engine/Cargo.toml stress_policy_interaction_fail_closed

echo "[dev-0040] PASS"
