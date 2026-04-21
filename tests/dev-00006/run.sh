#!/usr/bin/env bash
set -euo pipefail

for f in \
  services/market-normalization/app.py \
  services/bar-aggregation/app.py \
  services/gap-detection/app.py \
  services/backfill-worker/app.py; do
  python -m py_compile "$f"
  rg -n 'enable_auto_commit=False' "$f" >/dev/null
  rg -n 'is_message_processed\(' "$f" >/dev/null
  rg -n 'record_message_processed\(' "$f" >/dev/null
done

rg -n 'CREATE TABLE IF NOT EXISTS processed_message_ledger' infra/timescaledb/init/002_processed_message_ledger.sql >/dev/null

if [[ "${DEV00006_INTEGRATION:-0}" == "1" ]]; then
  tests/dev-00006/run-integration.sh
fi

echo "[dev-00006] checks passed"
