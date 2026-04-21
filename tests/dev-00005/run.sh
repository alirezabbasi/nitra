#!/usr/bin/env bash
set -euo pipefail

for f in \
  services/market-ingestion/app.py \
  services/market-normalization/app.py \
  services/bar-aggregation/app.py \
  services/gap-detection/app.py \
  services/backfill-worker/app.py; do
  [[ -f "$f" ]]
  python -m py_compile "$f"
done

rg -n 'market-ingestion:' docker-compose.yml >/dev/null
rg -n 'market-normalization:' docker-compose.yml >/dev/null
rg -n 'bar-aggregation:' docker-compose.yml >/dev/null
rg -n 'gap-detection:' docker-compose.yml >/dev/null
rg -n 'backfill-worker:' docker-compose.yml >/dev/null

rg -n 'INGESTION_RAW_TOPIC: raw.market.oanda' docker-compose.yml >/dev/null
rg -n 'NORMALIZER_OUTPUT_TOPIC: normalized.quote.fx' docker-compose.yml >/dev/null
rg -n 'BAR_OUTPUT_TOPIC: bar.1m' docker-compose.yml >/dev/null
rg -n 'GAP_OUTPUT_TOPIC: gap.events' docker-compose.yml >/dev/null
rg -n 'BACKFILL_REPLAY_TOPIC: replay.commands' docker-compose.yml >/dev/null

[[ -f docs/ingestion_docs/07-devdocs/01-development-environment/ingestion-service-env.md ]]

echo "[dev-00005] checks passed"
