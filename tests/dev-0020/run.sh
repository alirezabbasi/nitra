#!/usr/bin/env bash
set -euo pipefail

[[ -f services/execution-gateway/Cargo.toml ]]
[[ -f services/execution-gateway/src/main.rs ]]

export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/tmp/nitra-execution-gateway-target}"

cargo check --offline --manifest-path services/execution-gateway/Cargo.toml >/dev/null
cargo test --offline --manifest-path services/execution-gateway/Cargo.toml >/dev/null

rg -n 'EXECUTION_INPUT_TOPIC' services/execution-gateway/src/main.rs >/dev/null
rg -n 'EXEC_ORDER_SUBMITTED_TOPIC' services/execution-gateway/src/main.rs >/dev/null
rg -n 'EXEC_ORDER_UPDATED_TOPIC' services/execution-gateway/src/main.rs >/dev/null
rg -n 'EXEC_FILL_RECEIVED_TOPIC' services/execution-gateway/src/main.rs >/dev/null
rg -n 'EXEC_RECONCILIATION_ISSUE_TOPIC' services/execution-gateway/src/main.rs >/dev/null
rg -n 'execution_order_journal' services/execution-gateway/src/main.rs >/dev/null
rg -n 'audit_event_log' services/execution-gateway/src/main.rs >/dev/null
rg -n 'processed_message_ledger' services/execution-gateway/src/main.rs >/dev/null

[[ -f infra/timescaledb/init/009_execution_audit_journal.sql ]]
rg -n 'CREATE TABLE IF NOT EXISTS execution_order_journal' infra/timescaledb/init/009_execution_audit_journal.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS audit_event_log' infra/timescaledb/init/009_execution_audit_journal.sql >/dev/null

rg -n 'exec\.order_submitted\.v1' infra/kafka/topics.csv >/dev/null
rg -n 'exec\.order_updated\.v1' infra/kafka/topics.csv >/dev/null
rg -n 'exec\.fill_received\.v1' infra/kafka/topics.csv >/dev/null
rg -n 'exec\.reconciliation_issue\.v1' infra/kafka/topics.csv >/dev/null

rg -n 'EXECUTION_INPUT_TOPIC' docker-compose.yml >/dev/null
rg -n 'EXECUTION_GROUP_ID' docker-compose.yml >/dev/null

echo "[dev-0020] checks passed"
