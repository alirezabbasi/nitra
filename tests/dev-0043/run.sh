#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0043] FAIL: $1" >&2
  exit 1
}

echo "[dev-0043] checking audit taxonomy + incident bundle wiring..."
[[ -f infra/timescaledb/init/017_incident_evidence_bundle.sql ]] || fail "missing migration 017_incident_evidence_bundle.sql"
rg -n 'incident_evidence_bundle|export_incident_bundle' services/execution-gateway/src/main.rs >/dev/null || fail "missing incident bundle runtime hooks"
rg -n 'EXEC_AUDIT_TAXONOMY_VERSION|taxonomy_version|root_correlation_id|lineage' services/execution-gateway/src/main.rs >/dev/null || fail "missing audit taxonomy/lineage fields"

echo "[dev-0043] running execution-gateway regression tests..."
CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo test --manifest-path services/execution-gateway/Cargo.toml parse_intent_lineage_and_correlation
CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo test --manifest-path services/execution-gateway/Cargo.toml lifecycle_transition_guard_blocks_invalid_paths

echo "[dev-0043] PASS"
