#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

set -a
source .env
set +a

docker compose up -d --build timescaledb kafka market-normalization >/dev/null
scripts/kafka/bootstrap-topics.sh >/dev/null

MSG_ID="11111111-1111-1111-1111-111111111111"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
PAYLOAD=$(cat <<JSON
{"message_id":"$MSG_ID","emitted_at":"$NOW","schema_version":1,"headers":{},"payload":{"venue":"oanda","broker_symbol":"EUR_USD","event_ts_received":"$NOW","payload":{"bid":1.1,"ask":1.2,"mid":1.15,"sequence_id":"seq-dev-00006"},"source":"dev-00006.integration"},"retry":null}
JSON
)

printf '%s\n%s\n' "$PAYLOAD" "$PAYLOAD" | docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka:9092 --topic raw.market.oanda >/dev/null

for _ in $(seq 1 30); do
  RAW_COUNT=$(docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "SELECT COUNT(*) FROM raw_tick WHERE message_id='$MSG_ID'::uuid;" | tr -d '[:space:]')
  LEDGER_COUNT=$(docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "SELECT COUNT(*) FROM processed_message_ledger WHERE service_name='market_normalization' AND message_id='$MSG_ID'::uuid;" | tr -d '[:space:]')

  if [[ "$RAW_COUNT" == "1" && "$LEDGER_COUNT" == "1" ]]; then
    echo "[dev-00006] integration checks passed"
    exit 0
  fi
  sleep 2
done

echo "[dev-00006] integration check failed: raw_count=$RAW_COUNT ledger_count=$LEDGER_COUNT" >&2
exit 1
