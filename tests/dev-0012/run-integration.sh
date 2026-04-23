#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

set -a
source .env
set +a

docker compose up -d --build timescaledb kafka bar-aggregation gap-detection backfill-worker >/dev/null
scripts/kafka/bootstrap-topics.sh >/dev/null

T0="2026-01-01T00:00:10Z"
T1="2026-01-01T00:03:10Z"
T2="2026-01-01T00:04:10Z"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

emit_normalized() {
  local msg_id="$1"
  local event_ts="$2"
  local mid="$3"
  cat <<JSON
{"message_id":"$msg_id","emitted_at":"$NOW","schema_version":1,"headers":{},"payload":{"event_id":"$msg_id","venue":"oanda","asset_class":"fx","broker_symbol":"EUR_USD","canonical_symbol":"EURUSD","event_type":"quote","event_ts_exchange":"$event_ts","event_ts_received":"$event_ts","bid":$mid,"ask":$mid,"mid":$mid,"last":null,"volume":null,"sequence_id":"$msg_id","source_checksum":"n/a","ingestion_run_id":"dev-0012","schema_version":1},"retry":null}
JSON
}

{
  emit_normalized "22222222-2222-2222-2222-222222222220" "$T0" "1.1000"
  emit_normalized "22222222-2222-2222-2222-222222222221" "$T1" "1.1010"
  emit_normalized "22222222-2222-2222-2222-222222222222" "$T2" "1.1020"
} | docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka:9092 --topic normalized.quote.fx >/dev/null

for _ in $(seq 1 45); do
  BAR_ROWS=$(docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "SELECT COUNT(*) FROM ohlcv_bar WHERE venue='oanda' AND canonical_symbol='EURUSD' AND timeframe='1m' AND bucket_start IN ('2026-01-01T00:00:00Z'::timestamptz,'2026-01-01T00:03:00Z'::timestamptz);" | tr -d '[:space:]')

  B_COUNT=$(docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "SELECT COUNT(*) FROM processed_message_ledger WHERE service_name='bar_aggregation' AND processed_at > now() - interval '5 minutes';" | tr -d '[:space:]')
  G_COUNT=$(docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "SELECT COUNT(*) FROM processed_message_ledger WHERE service_name='gap_detection' AND processed_at > now() - interval '5 minutes';" | tr -d '[:space:]')
  BF_COUNT=$(docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A -c "SELECT COUNT(*) FROM processed_message_ledger WHERE service_name='backfill_worker' AND processed_at > now() - interval '5 minutes';" | tr -d '[:space:]')

  if [[ "$BAR_ROWS" -ge 2 && "$B_COUNT" -ge 1 && "$G_COUNT" -ge 1 && "$BF_COUNT" -ge 1 ]]; then
    echo "[dev-0012] integration checks passed"
    exit 0
  fi
  sleep 2
done

echo "[dev-0012] integration check failed: bar_rows=$BAR_ROWS bar_ledger=$B_COUNT gap_ledger=$G_COUNT backfill_ledger=$BF_COUNT" >&2
exit 1
