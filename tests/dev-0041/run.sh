#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0041] FAIL: $1" >&2
  exit 1
}

echo "[dev-0041] checking execution lifecycle hardening wiring..."
rg -n 'is_valid_lifecycle_transition|invalid_lifecycle_transition' services/execution-gateway/src/main.rs >/dev/null || fail "missing lifecycle guards"
rg -n 'stale_command|duplicate_command' services/execution-gateway/src/main.rs >/dev/null || fail "missing stale/duplicate command controls"
rg -n 'reconciliation_sla_breach|sla_seconds|age_seconds' services/execution-gateway/src/main.rs >/dev/null || fail "missing reconciliation SLA context"
rg -n 'EXEC_COMMAND_STALE_AFTER_SECS|EXEC_COMMAND_DUPLICATE_WINDOW_SECS|EXEC_RECONCILIATION_SLA_SECS' services/execution-gateway/src/main.rs >/dev/null || fail "missing new execution env controls"

echo "[dev-0041] running lifecycle and regression tests..."
CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo test --manifest-path services/execution-gateway/Cargo.toml lifecycle_transition_guard_blocks_invalid_paths
CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo test --manifest-path services/execution-gateway/Cargo.toml backoff_is_bounded

echo "[dev-0041] PASS"
