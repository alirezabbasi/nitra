#!/usr/bin/env bash
set -euo pipefail

[[ -f services/structure-engine/Cargo.toml ]]
[[ -f services/structure-engine/src/main.rs ]]

export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/tmp/nitra-structure-engine-target}"

cargo check --offline --manifest-path services/structure-engine/Cargo.toml >/dev/null
cargo test --offline --manifest-path services/structure-engine/Cargo.toml >/dev/null

rg -n 'STRUCTURE_INPUT_TOPIC' services/structure-engine/src/main.rs >/dev/null
rg -n 'STRUCTURE_SNAPSHOT_TOPIC' services/structure-engine/src/main.rs >/dev/null
rg -n 'STRUCTURE_PULLBACK_TOPIC' services/structure-engine/src/main.rs >/dev/null
rg -n 'STRUCTURE_MINOR_TOPIC' services/structure-engine/src/main.rs >/dev/null
rg -n 'STRUCTURE_MAJOR_TOPIC' services/structure-engine/src/main.rs >/dev/null
rg -n 'structure_state' services/structure-engine/src/main.rs >/dev/null
rg -n 'processed_message_ledger' services/structure-engine/src/main.rs >/dev/null
rg -n 'apply_bar_transition' services/structure-engine/src/main.rs >/dev/null

[[ -f infra/timescaledb/init/007_structure_state.sql ]]
rg -n 'CREATE TABLE IF NOT EXISTS structure_state' infra/timescaledb/init/007_structure_state.sql >/dev/null

rg -n 'structure\.snapshot\.v1' infra/kafka/topics.csv >/dev/null
rg -n 'structure\.pullback\.v1' infra/kafka/topics.csv >/dev/null
rg -n 'structure\.minor_confirmed\.v1' infra/kafka/topics.csv >/dev/null
rg -n 'structure\.major_confirmed\.v1' infra/kafka/topics.csv >/dev/null

rg -n 'STRUCTURE_INPUT_TOPIC' docker-compose.yml >/dev/null
rg -n 'STRUCTURE_GROUP_ID' docker-compose.yml >/dev/null

echo "[dev-0018] checks passed"
