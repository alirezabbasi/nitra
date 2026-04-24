#!/usr/bin/env bash
set -euo pipefail

for f in \
  services/bar-aggregation/Cargo.toml \
  services/bar-aggregation/src/main.rs \
  services/gap-detection/Cargo.toml \
  services/gap-detection/src/main.rs \
  services/backfill-worker/Cargo.toml \
  services/backfill-worker/src/main.rs; do
  [[ -f "$f" ]]
done

cargo check --manifest-path services/bar-aggregation/Cargo.toml >/dev/null
cargo check --manifest-path services/gap-detection/Cargo.toml >/dev/null
cargo check --manifest-path services/backfill-worker/Cargo.toml >/dev/null
rg -n 'choose_event_timestamp' services/bar-aggregation/src/main.rs >/dev/null
rg -n 'falls_back_to_received_when_exchange_stale' services/bar-aggregation/src/main.rs >/dev/null

rg -n 'BAR_INPUT_TOPIC: normalized.quote.fx' docker-compose.yml >/dev/null
rg -n 'BAR_OUTPUT_TOPIC: bar.1m' docker-compose.yml >/dev/null
rg -n 'GAP_INPUT_TOPIC: bar.1m' docker-compose.yml >/dev/null
rg -n 'GAP_OUTPUT_TOPIC: gap.events' docker-compose.yml >/dev/null
rg -n 'BACKFILL_INPUT_TOPIC: gap.events' docker-compose.yml >/dev/null
rg -n 'BACKFILL_REPLAY_TOPIC: replay.commands' docker-compose.yml >/dev/null

if [[ "${DEV0012_INTEGRATION:-0}" == "1" ]]; then
  tests/dev-0012/run-integration.sh
fi

echo "[dev-0012] checks passed"
