#!/usr/bin/env bash
set -euo pipefail

[[ -f services/portfolio-engine/Cargo.toml ]]
[[ -f services/portfolio-engine/src/main.rs ]]
[[ -f services/risk-engine/Cargo.toml ]]
[[ -f services/risk-engine/src/main.rs ]]

export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-/tmp/nitra-portfolio-risk-target}"

cargo check --offline --manifest-path services/portfolio-engine/Cargo.toml >/dev/null
cargo test --offline --manifest-path services/portfolio-engine/Cargo.toml >/dev/null
cargo check --offline --manifest-path services/risk-engine/Cargo.toml >/dev/null
cargo test --offline --manifest-path services/risk-engine/Cargo.toml >/dev/null

rg -n 'PORTFOLIO_INPUT_FILL_TOPIC' services/portfolio-engine/src/main.rs >/dev/null
rg -n 'PORTFOLIO_SNAPSHOT_TOPIC' services/portfolio-engine/src/main.rs >/dev/null
rg -n 'portfolio_position_state' services/portfolio-engine/src/main.rs >/dev/null
rg -n 'portfolio_account_state' services/portfolio-engine/src/main.rs >/dev/null
rg -n 'portfolio_fill_log' services/portfolio-engine/src/main.rs >/dev/null

rg -n 'RISK_MAX_SYMBOL_EXPOSURE_NOTIONAL' services/risk-engine/src/main.rs >/dev/null
rg -n 'RISK_MAX_PORTFOLIO_GROSS_EXPOSURE_NOTIONAL' services/risk-engine/src/main.rs >/dev/null
rg -n 'RISK_MIN_AVAILABLE_EQUITY' services/risk-engine/src/main.rs >/dev/null
rg -n 'load_portfolio_snapshot' services/risk-engine/src/main.rs >/dev/null

[[ -f infra/timescaledb/init/011_portfolio_state.sql ]]
rg -n 'CREATE TABLE IF NOT EXISTS portfolio_position_state' infra/timescaledb/init/011_portfolio_state.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS portfolio_account_state' infra/timescaledb/init/011_portfolio_state.sql >/dev/null

rg -n 'portfolio\.snapshot\.v1' infra/kafka/topics.csv >/dev/null

rg -n 'portfolio-engine:' docker-compose.yml >/dev/null
rg -n 'PORTFOLIO_SNAPSHOT_TOPIC' docker-compose.yml >/dev/null
rg -n 'RISK_MAX_SYMBOL_EXPOSURE_NOTIONAL' docker-compose.yml >/dev/null

echo "[dev-0023] checks passed"
