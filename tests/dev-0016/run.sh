#!/usr/bin/env bash
set -euo pipefail

[[ -f infra/timescaledb/init/005_venue_market.sql ]]
rg -n 'CREATE TABLE IF NOT EXISTS venue_market' infra/timescaledb/init/005_venue_market.sql >/dev/null
rg -n 'ingest_enabled BOOLEAN NOT NULL DEFAULT TRUE' infra/timescaledb/init/005_venue_market.sql >/dev/null

python -m py_compile services/charting/app.py
rg -n '/api/v1/venues' services/charting/app.py >/dev/null
rg -n '/api/v1/ingestion/start' services/charting/app.py >/dev/null
rg -n -F '/api/v1/venues/{venue}/markets' services/charting/app.py >/dev/null

rg -n 'settings-btn' services/charting/static/index.html >/dev/null
rg -n 'settings-overlay' services/charting/static/index.html >/dev/null
rg -n '/api/v1/ingestion/start' services/charting/static/index.html >/dev/null

cargo check --manifest-path services/market-ingestion/Cargo.toml >/dev/null
rg -n 'load_symbols_from_db' services/market-ingestion/src/main.rs >/dev/null
rg -n 'fx_market_weekend_closed' services/market-ingestion/src/main.rs >/dev/null

rg -n -F 'INGESTION_SYMBOL_SOURCE: ${INGESTION_SYMBOL_SOURCE:-database}' docker-compose.yml >/dev/null
rg -n -F 'FX_WEEKEND_END_HOUR_UTC' docker-compose.yml >/dev/null

echo "[dev-0016] checks passed"
