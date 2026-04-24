#!/usr/bin/env bash
set -euo pipefail

for f in \
  services/gap-detection/src/main.rs \
  services/backfill-worker/src/main.rs \
  services/replay-controller/src/main.rs \
  infra/timescaledb/init/004_gap_backfill_runtime.sql; do
  [[ -f "$f" ]]
done

cargo test --manifest-path services/gap-detection/Cargo.toml >/dev/null
cargo test --manifest-path services/backfill-worker/Cargo.toml >/dev/null
cargo test --manifest-path services/replay-controller/Cargo.toml >/dev/null

rg -n 'CREATE TABLE IF NOT EXISTS coverage_state' infra/timescaledb/init/004_gap_backfill_runtime.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS gap_log' infra/timescaledb/init/004_gap_backfill_runtime.sql >/dev/null
rg -n 'CREATE TABLE IF NOT EXISTS backfill_jobs' infra/timescaledb/init/004_gap_backfill_runtime.sql >/dev/null

rg -n 'GAP_STARTUP_COVERAGE_DAYS' docker-compose.yml >/dev/null
rg -n 'GAP_SYMBOL_REGISTRY_PATH' docker-compose.yml >/dev/null
rg -n 'GAP_PERIODIC_SCAN_ENABLED' docker-compose.yml >/dev/null
rg -n 'GAP_PERIODIC_SCAN_INTERVAL_SECS' docker-compose.yml >/dev/null
rg -n 'periodic_coverage_scan' services/gap-detection/src/main.rs >/dev/null
rg -n 'stream_recovery' services/gap-detection/src/main.rs >/dev/null
rg -n 'BACKFILL_FETCH_CHUNK_MINUTES' docker-compose.yml >/dev/null
rg -n 'REPLAY_INPUT_TOPIC: replay.commands' docker-compose.yml >/dev/null
rg -n 'REPLAY_HISTORY_ENABLED' docker-compose.yml >/dev/null
rg -n 'fetch_venue_history_bars' services/replay-controller/src/main.rs >/dev/null

echo "[dev-0013] checks passed"
