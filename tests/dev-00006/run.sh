#!/usr/bin/env bash
set -euo pipefail

for f in \
  services/bar-aggregation/Cargo.toml \
  services/gap-detection/Cargo.toml \
  services/backfill-worker/Cargo.toml \
  services/bar-aggregation/src/main.rs \
  services/gap-detection/src/main.rs \
  services/backfill-worker/src/main.rs; do
  [[ -f "$f" ]]
done

cargo check --manifest-path services/bar-aggregation/Cargo.toml >/dev/null
cargo check --manifest-path services/gap-detection/Cargo.toml >/dev/null
cargo check --manifest-path services/backfill-worker/Cargo.toml >/dev/null
rg -n 'enable.auto.commit", "false"' services/bar-aggregation/src/main.rs >/dev/null
rg -n 'enable.auto.commit", "false"' services/gap-detection/src/main.rs >/dev/null
rg -n 'enable.auto.commit", "false"' services/backfill-worker/src/main.rs >/dev/null
rg -n 'processed_message_ledger' services/bar-aggregation/src/main.rs >/dev/null
rg -n 'processed_message_ledger' services/gap-detection/src/main.rs >/dev/null
rg -n 'processed_message_ledger' services/backfill-worker/src/main.rs >/dev/null
rg -n 'ON CONFLICT DO NOTHING' services/bar-aggregation/src/main.rs >/dev/null
rg -n 'ON CONFLICT DO NOTHING' services/gap-detection/src/main.rs >/dev/null
rg -n 'ON CONFLICT DO NOTHING' services/backfill-worker/src/main.rs >/dev/null
rg -n 'commit_message\(' services/bar-aggregation/src/main.rs >/dev/null
rg -n 'commit_message\(' services/gap-detection/src/main.rs >/dev/null
rg -n 'commit_message\(' services/backfill-worker/src/main.rs >/dev/null

[[ -f services/market-normalization/Cargo.toml ]]
[[ -f services/market-normalization/src/main.rs ]]
cargo check --manifest-path services/market-normalization/Cargo.toml >/dev/null
rg -n 'enable.auto.commit", "false"' services/market-normalization/src/main.rs >/dev/null
rg -n 'processed_message_ledger' services/market-normalization/src/main.rs >/dev/null
rg -n 'ON CONFLICT DO NOTHING' services/market-normalization/src/main.rs >/dev/null
rg -n 'commit_message\(' services/market-normalization/src/main.rs >/dev/null

rg -n 'CREATE TABLE IF NOT EXISTS processed_message_ledger' infra/timescaledb/init/002_processed_message_ledger.sql >/dev/null

if [[ "${DEV00006_INTEGRATION:-0}" == "1" ]]; then
  tests/dev-00006/run-integration.sh
fi

echo "[dev-00006] checks passed"
