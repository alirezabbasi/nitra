#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-http://localhost:8110}"
LOOKBACK_DAYS="${LOOKBACK_DAYS:-90}"
CHUNK_DAYS="${CHUNK_DAYS:-7}"

SYMBOLS=(
  "capital EURUSD"
  "capital GBPUSD"
  "coinbase DOGEUSD"
  "coinbase TONUSD"
  "oanda EURUSD"
  "oanda GBPUSD"
  "oanda USDJPY"
)

iso_utc() {
  date -u -d "$1" +"%Y-%m-%dT%H:%M:%S+00:00"
}

echo "== Per-symbol adapter check =="
for pair in "${SYMBOLS[@]}"; do
  venue="${pair%% *}"
  symbol="${pair##* }"
  echo "-- $venue/$symbol"
  curl -sS -X POST "$HOST/api/v1/backfill/adapter-check" \
    -H "Content-Type: application/json" \
    -d "{\"venue\":\"$venue\",\"symbol\":\"$symbol\"}"
  echo
done

echo "== Chunked backfill window recovery =="
end_epoch="$(date -u +%s)"
start_epoch="$((end_epoch - LOOKBACK_DAYS*24*60*60))"
chunk_secs="$((CHUNK_DAYS*24*60*60))"

for pair in "${SYMBOLS[@]}"; do
  venue="${pair%% *}"
  symbol="${pair##* }"
  echo "== $venue/$symbol =="
  cursor="$end_epoch"
  while [ "$cursor" -gt "$start_epoch" ]; do
    from_epoch="$((cursor - chunk_secs + 60))"
    if [ "$from_epoch" -lt "$start_epoch" ]; then
      from_epoch="$start_epoch"
    fi
    from_ts="$(iso_utc "@$from_epoch")"
    to_ts="$(iso_utc "@$cursor")"
    echo "window: $from_ts .. $to_ts"
    curl -sS -X POST "$HOST/api/v1/backfill/window" \
      -H "Content-Type: application/json" \
      -d "{\"venue\":\"$venue\",\"symbol\":\"$symbol\",\"from_ts\":\"$from_ts\",\"to_ts\":\"$to_ts\"}" >/dev/null || true
    cursor="$((from_epoch - 60))"
    sleep 1
  done
done

echo "done"
