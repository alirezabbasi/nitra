#!/usr/bin/env bash
set -euo pipefail

[[ -f services/risk-engine/Cargo.toml ]]
[[ -f services/risk-engine/src/main.rs ]]

export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/tmp/nitra-risk-engine-target}"

cargo check --offline --manifest-path services/risk-engine/Cargo.toml >/dev/null
cargo test --offline --manifest-path services/risk-engine/Cargo.toml >/dev/null

rg -n 'RISK_INPUT_TOPIC' services/risk-engine/src/main.rs >/dev/null
rg -n 'RISK_CHECKED_TOPIC' services/risk-engine/src/main.rs >/dev/null
rg -n 'RISK_VIOLATION_TOPIC' services/risk-engine/src/main.rs >/dev/null
rg -n 'evaluate_policy' services/risk-engine/src/main.rs >/dev/null
rg -n 'risk_state' services/risk-engine/src/main.rs >/dev/null
rg -n 'risk_decision_log' services/risk-engine/src/main.rs >/dev/null
rg -n 'processed_message_ledger' services/risk-engine/src/main.rs >/dev/null

[[ -f infra/timescaledb/init/008_risk_state.sql ]]
rg -n 'CREATE TABLE IF NOT EXISTS risk_state' infra/timescaledb/init/008_risk_state.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS risk_decision_log' infra/timescaledb/init/008_risk_state.sql >/dev/null

rg -n 'decision\.risk_checked\.v1' infra/kafka/topics.csv >/dev/null
rg -n 'ops\.policy_violation\.v1' infra/kafka/topics.csv >/dev/null

rg -n 'RISK_INPUT_TOPIC' docker-compose.yml >/dev/null
rg -n 'RISK_GROUP_ID' docker-compose.yml >/dev/null

echo "[dev-0019] checks passed"
