#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0037] FAIL: $1" >&2
  exit 1
}

echo "[dev-0037] checking structure-state transition-reason persistence wiring..."
rg -n "last_transition_reason" services/structure-engine/src/main.rs >/dev/null || fail "missing last_transition_reason runtime wiring"
rg -n "last_transition_reason" infra/timescaledb/init/012_structure_transition_reason.sql >/dev/null || fail "missing DB migration for transition reason"

echo "[dev-0037] checking out-of-order replay guard..."
rg -n "bar\.bucket_start <= previous_state\.last_bucket_start" services/structure-engine/src/main.rs >/dev/null || fail "missing out-of-order bar guard"

echo "[dev-0037] running deterministic transition hardening tests..."
CARGO_TARGET_DIR=/tmp/nitra-structure-engine-target cargo test --manifest-path services/structure-engine/Cargo.toml rejects_out_of_order_transition
CARGO_TARGET_DIR=/tmp/nitra-structure-engine-target cargo test --manifest-path services/structure-engine/Cargo.toml rejects_illegal_minor_reason_invariant
CARGO_TARGET_DIR=/tmp/nitra-structure-engine-target cargo test --manifest-path services/structure-engine/Cargo.toml replay_sequence_is_deterministic

echo "[dev-0037] PASS"
