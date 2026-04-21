#!/usr/bin/env bash
set -euo pipefail

[[ -f infra/timescaledb/init/001_ohlcv_bar.sql ]]
[[ -f infra/timescaledb/init/002_processed_message_ledger.sql ]]
[[ -f infra/timescaledb/init/003_market_event_entities.sql ]]

rg -n 'CREATE TABLE IF NOT EXISTS ohlcv_bar' infra/timescaledb/init/001_ohlcv_bar.sql >/dev/null
rg -n 'CREATE EXTENSION IF NOT EXISTS timescaledb' infra/timescaledb/init/001_ohlcv_bar.sql >/dev/null
rg -n 'PRIMARY KEY \(venue, canonical_symbol, timeframe, bucket_start\)' infra/timescaledb/init/001_ohlcv_bar.sql >/dev/null

rg -n 'CREATE TABLE IF NOT EXISTS processed_message_ledger' infra/timescaledb/init/002_processed_message_ledger.sql >/dev/null
rg -n 'PRIMARY KEY \(service_name, message_id\)' infra/timescaledb/init/002_processed_message_ledger.sql >/dev/null
rg -n 'UNIQUE \(service_name, source_topic, source_partition, source_offset\)' infra/timescaledb/init/002_processed_message_ledger.sql >/dev/null

rg -n 'CREATE TABLE IF NOT EXISTS raw_tick' infra/timescaledb/init/003_market_event_entities.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS trade_print' infra/timescaledb/init/003_market_event_entities.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS book_event' infra/timescaledb/init/003_market_event_entities.sql >/dev/null

rg -n './infra/timescaledb/init:/docker-entrypoint-initdb.d:ro' docker-compose.yml >/dev/null

echo "[dev-00004] checks passed"
