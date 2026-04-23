#!/usr/bin/env bash
set -euo pipefail

for f in \
  services/ingestion/contracts.py \
  services/ingestion/domain.py \
  services/ingestion/mock_pricing.py \
  services/market-ingestion/app.py \
  services/market-normalization/app.py \
  services/bar-aggregation/app.py \
  services/gap-detection/app.py \
  services/backfill-worker/app.py; do
  [[ -f "$f" ]]
  python -m py_compile "$f"
done

rg -n 'market-ingestion:' docker-compose.yml >/dev/null
rg -n 'market-ingestion-capital:' docker-compose.yml >/dev/null
rg -n 'market-ingestion-coinbase:' docker-compose.yml >/dev/null
rg -n 'market-normalization:' docker-compose.yml >/dev/null
rg -n 'bar-aggregation:' docker-compose.yml >/dev/null
rg -n 'gap-detection:' docker-compose.yml >/dev/null
rg -n 'backfill-worker:' docker-compose.yml >/dev/null

rg -n -F 'INGESTION_RAW_TOPIC: ${OANDA_RAW_TOPIC}' docker-compose.yml >/dev/null
rg -n -F 'INGESTION_RAW_TOPIC: ${CAPITAL_RAW_TOPIC}' docker-compose.yml >/dev/null
rg -n -F 'INGESTION_RAW_TOPIC: ${COINBASE_RAW_TOPIC}' docker-compose.yml >/dev/null
rg -n -F 'INGESTION_ENABLED_INSTRUMENTS: ${OANDA_ENABLED_INSTRUMENTS}' docker-compose.yml >/dev/null
rg -n -F 'INGESTION_ENABLED_INSTRUMENTS: ${CAPITAL_ENABLED_INSTRUMENTS}' docker-compose.yml >/dev/null
rg -n -F 'INGESTION_ENABLED_INSTRUMENTS: ${COINBASE_ENABLED_INSTRUMENTS}' docker-compose.yml >/dev/null
rg -n -F 'OANDA_STREAM_URL: ${OANDA_STREAM_URL}' docker-compose.yml >/dev/null
rg -n -F 'CAPITAL_API_URL: ${CAPITAL_API_URL}' docker-compose.yml >/dev/null
rg -n -F 'COINBASE_WS_URL: ${COINBASE_WS_URL}' docker-compose.yml >/dev/null
rg -n 'NORMALIZER_OUTPUT_TOPIC: normalized.quote.fx' docker-compose.yml >/dev/null
rg -n 'BAR_OUTPUT_TOPIC: bar.1m' docker-compose.yml >/dev/null
rg -n 'GAP_OUTPUT_TOPIC: gap.events' docker-compose.yml >/dev/null
rg -n 'BACKFILL_REPLAY_TOPIC: replay.commands' docker-compose.yml >/dev/null

[[ -f docs/design/ingestion/07-devdocs/01-development-environment/ingestion-service-env.md ]]
[[ -f infra/symbols/registry.v1.json ]]

echo "[dev-00005] checks passed"
