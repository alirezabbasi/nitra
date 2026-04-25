#!/usr/bin/env bash
set -euo pipefail

[[ -f services/backfill-worker/Cargo.toml ]]
[[ -f services/backfill-worker/src/main.rs ]]
cargo check --manifest-path services/backfill-worker/Cargo.toml >/dev/null

[[ -f services/replay-controller/Cargo.toml ]]
[[ -f services/replay-controller/src/main.rs ]]
cargo check --manifest-path services/replay-controller/Cargo.toml >/dev/null

rg -n 'BACKFILL_RECOVERY_ENABLED' services/backfill-worker/src/main.rs >/dev/null
rg -n 'reset_stale_running_jobs' services/backfill-worker/src/main.rs >/dev/null
rg -n 'reenqueue_queued_jobs' services/backfill-worker/src/main.rs >/dev/null
rg -n 'BACKFILL_QUEUED_STALE_SECS' services/backfill-worker/src/main.rs >/dev/null
rg -n "ra\\.status = 'queued'" services/backfill-worker/src/main.rs >/dev/null
rg -n "COALESCE\\(bj\\.last_enqueued_at, bj\\.created_at\\) ASC" services/backfill-worker/src/main.rs >/dev/null
rg -n 'last_enqueued_at' services/backfill-worker/src/main.rs >/dev/null
rg -n 'enqueue_count' services/backfill-worker/src/main.rs >/dev/null

rg -n 'REPLAY_OANDA_INSTRUMENT_MAP' services/replay-controller/src/main.rs >/dev/null
rg -n 'REPLAY_COINBASE_USER_AGENT' services/replay-controller/src/main.rs >/dev/null
rg -n 'REPLAY_WORKER_COUNT' services/replay-controller/src/main.rs >/dev/null
rg -n -F 'run_worker(' services/replay-controller/src/main.rs >/dev/null
rg -n 'header\("User-Agent"' services/replay-controller/src/main.rs >/dev/null
rg -n 'symbol_for_oanda\(' services/replay-controller/src/main.rs >/dev/null

[[ -f infra/timescaledb/init/006_backfill_job_recovery_columns.sql ]]
rg -n 'ADD COLUMN IF NOT EXISTS enqueue_count' infra/timescaledb/init/006_backfill_job_recovery_columns.sql >/dev/null
rg -n 'ADD COLUMN IF NOT EXISTS last_enqueued_at' infra/timescaledb/init/006_backfill_job_recovery_columns.sql >/dev/null

rg -n 'BACKFILL_RECOVERY_ENABLED' docker-compose.yml >/dev/null
rg -n 'BACKFILL_QUEUED_STALE_SECS' docker-compose.yml >/dev/null
rg -n 'REPLAY_WORKER_COUNT' docker-compose.yml >/dev/null
rg -n 'REPLAY_COINBASE_USER_AGENT' docker-compose.yml >/dev/null

echo "[dev-0017] checks passed"
