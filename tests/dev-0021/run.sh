#!/usr/bin/env bash
set -euo pipefail

[[ -f services/execution-gateway/Cargo.toml ]]
[[ -f services/execution-gateway/src/main.rs ]]

export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/tmp/nitra-execution-gateway-target}"

cargo check --offline --manifest-path services/execution-gateway/Cargo.toml >/dev/null
cargo test --offline --manifest-path services/execution-gateway/Cargo.toml >/dev/null

rg -n 'EXECUTION_COMMAND_TOPIC' services/execution-gateway/src/main.rs >/dev/null
rg -n 'EXECUTION_BROKER_ACK_TOPIC' services/execution-gateway/src/main.rs >/dev/null
rg -n 'EXEC_BROKER_SUBMIT_URL' services/execution-gateway/src/main.rs >/dev/null
rg -n 'EXEC_BROKER_AMEND_URL' services/execution-gateway/src/main.rs >/dev/null
rg -n 'EXEC_BROKER_CANCEL_URL' services/execution-gateway/src/main.rs >/dev/null
rg -n 'execution_command_log' services/execution-gateway/src/main.rs >/dev/null
rg -n 'handle_broker_ack' services/execution-gateway/src/main.rs >/dev/null
rg -n 'handle_order_command' services/execution-gateway/src/main.rs >/dev/null

[[ -f infra/timescaledb/init/010_execution_broker_adapter.sql ]]
rg -n 'ALTER TABLE execution_order_journal' infra/timescaledb/init/010_execution_broker_adapter.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS execution_command_log' infra/timescaledb/init/010_execution_broker_adapter.sql >/dev/null

rg -n 'exec\.order_command\.v1' infra/kafka/topics.csv >/dev/null
rg -n 'broker\.execution\.ack\.v1' infra/kafka/topics.csv >/dev/null

rg -n 'EXECUTION_COMMAND_TOPIC' docker-compose.yml >/dev/null
rg -n 'EXECUTION_BROKER_ACK_TOPIC' docker-compose.yml >/dev/null

echo "[dev-0021] checks passed"
