#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0036] FAIL: $1" >&2
  exit 1
}

echo "[dev-0036] checking canonical second-chain topic registry..."
for topic in \
  structure.snapshot.v1 \
  decision.signal_scored.v1 \
  decision.risk_checked.v1 \
  exec.order_submitted.v1 \
  exec.order_updated.v1 \
  exec.fill_received.v1 \
  portfolio.snapshot.v1; do
  rg -n "^${topic}," infra/kafka/topics.csv >/dev/null || fail "missing topic in infra/kafka/topics.csv: ${topic}"
done

echo "[dev-0036] checking DEV-00036 contract schema artifacts..."
SCHEMA_DIR="docs/design/ingestion/07-devdocs/03-lld-data-model/contracts/second-chain"
for schema in \
  structure.snapshot.v1.schema.json \
  features.snapshot.v1.schema.json \
  decision.signal_scored.v1.schema.json \
  decision.risk_checked.v1.schema.json \
  exec.order_submitted.v1.schema.json \
  exec.order_updated.v1.schema.json \
  exec.fill_received.v1.schema.json \
  portfolio.snapshot.v1.schema.json \
  audit.event.v1.schema.json; do
  [[ -f "$SCHEMA_DIR/$schema" ]] || fail "missing schema artifact: $SCHEMA_DIR/$schema"
  rg -n '"required"\s*:\s*\[' "$SCHEMA_DIR/$schema" >/dev/null || fail "schema missing required-field contract: $schema"
done

echo "[dev-0036] checking deterministic replay/equivalence unit tests..."
rg -n "replay_sequence_is_deterministic" services/structure-engine/src/main.rs >/dev/null || fail "missing structure deterministic test"
rg -n "risk_policy_evaluation_is_deterministic" services/risk-engine/src/main.rs >/dev/null || fail "missing risk deterministic test"

echo "[dev-0036] running deterministic unit tests..."
CARGO_TARGET_DIR=/tmp/nitra-structure-engine-target cargo test --manifest-path services/structure-engine/Cargo.toml replay_sequence_is_deterministic
CARGO_TARGET_DIR=/tmp/nitra-risk-engine-target cargo test --manifest-path services/risk-engine/Cargo.toml risk_policy_evaluation_is_deterministic

echo "[dev-0036] PASS"
