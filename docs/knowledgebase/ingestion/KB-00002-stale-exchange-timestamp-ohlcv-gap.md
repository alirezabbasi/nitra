# KB-00002: `raw_tick` Has OANDA/Capital But `ohlcv_bar` Shows Only Coinbase

## Problem

After stack startup/restart, `raw_tick` ingestion is healthy for `oanda`, `capital`, and `coinbase`, but `ohlcv_bar` only contains Coinbase candles.

Recurrence note:
- This failure mode reoccurred (reported as second occurrence) in April 2026.

## Symptoms

- `raw_tick` grouped by venue shows all connectors active.
- `normalized.quote.fx` contains OANDA and Capital events with valid `mid`.
- `bar.1m` and `ohlcv_bar` initially show Coinbase-only candles.
- OANDA/Capital charts appear empty or stale despite incoming ticks.

## RCA

- Bar aggregation bucketed strictly on `event_ts_exchange`.
- For OANDA/Capital, adapters can emit stale/frozen exchange timestamps for quote events.
- With stale exchange time, minute bucket rollover does not advance for those venues.
- Without rollover, in-memory bar state is not flushed to `ohlcv_bar`.

## Resolution

- In `services/bar-aggregation/src/main.rs`, choose event timestamp with sanity bounds:
  - use `event_ts_exchange` when fresh,
  - fallback to `event_ts_received` when exchange time is stale or far-future.
- Rebuild/restart `bar-aggregation` service to apply the fix.
- Reference implementation commit: `a0040b8`.

## Validation

1. Check raw ingest by venue:
```sql
SELECT venue, COUNT(*) FROM raw_tick GROUP BY venue ORDER BY venue;
```
2. Confirm normalized stream includes OANDA/Capital with `mid`.
3. After at least one minute rollover, verify OHLCV by venue:
```sql
SELECT venue, COUNT(*) AS bars, MAX(bucket_start) AS last_bar
FROM ohlcv_bar
GROUP BY venue
ORDER BY venue;
```
4. Expect non-zero rows for `capital`, `oanda`, and `coinbase`.

## Guardrails

- 90-day backfill ownership is in ingestion deterministic services (`gap-detection` -> `backfill-worker` -> `replay-controller`), not in `charting`.
- Charting availability is not a precondition for 90-day recovery. If charting is down, ingestion backfill must continue and converge coverage.
- Keep timestamp fallback logic covered by tests:
  - `choose_event_timestamp_uses_exchange_when_fresh`
  - `choose_event_timestamp_falls_back_to_received_when_exchange_stale`
- Keep CI guard in `tests/dev-0012/run.sh` for fallback presence.
- During runtime incidents, always inspect both streams:
  - `normalized.quote.fx` (input health)
  - `bar.1m` + `ohlcv_bar` (aggregation/flush health)
- Linked bug record: `docs/development/debugging/BUG-00008.md`.
