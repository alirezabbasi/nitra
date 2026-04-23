#!/usr/bin/env bash
set -euo pipefail

for f in \
  services/gap-detection/src/main.rs \
  services/backfill-worker/src/main.rs \
  infra/timescaledb/init/004_gap_backfill_runtime.sql; do
  [[ -f "$f" ]]
done

cargo test --manifest-path services/gap-detection/Cargo.toml >/dev/null
cargo test --manifest-path services/backfill-worker/Cargo.toml >/dev/null

rg -n 'CREATE TABLE IF NOT EXISTS coverage_state' infra/timescaledb/init/004_gap_backfill_runtime.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS gap_log' infra/timescaledb/init/004_gap_backfill_runtime.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS backfill_jobs' infra/timescaledb/init/004_gap_backfill_runtime.sql >/dev/null

rg -n 'GAP_STARTUP_COVERAGE_DAYS' docker-compose.yml >/dev/null
rg -n 'GAP_SYMBOL_REGISTRY_PATH' docker-compose.yml >/dev/null
rg -n 'BACKFILL_FETCH_CHUNK_MINUTES' docker-compose.yml >/dev/null

echo "[dev-0013] checks passed"
