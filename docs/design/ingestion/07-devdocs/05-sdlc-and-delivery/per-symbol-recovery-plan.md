# Per-Symbol Recovery Plan (Backfill-First)

## Goal

Recover symbols that fail ingestion KPI with a deterministic order:

1. adapter readiness
2. recent-window continuity
3. full lookback completion
4. KPI verification

## KPI Targets

- 1m bars depth: `>= 130000` for continuous venues (crypto).
- Tick freshness: last `raw_tick.event_ts_received` within 5 minutes.
- FX venues (`capital`, `oanda`) use weekday-only continuity policy in recovery APIs. Their effective 90-day minute expectation is lower than continuous crypto.

## Recovery Order

Run symbols in this priority:

1. capital/EURUSD
2. capital/GBPUSD
3. coinbase/DOGEUSD
4. coinbase/TONUSD
5. oanda/EURUSD
6. oanda/GBPUSD
7. oanda/USDJPY

Rationale: lowest-coverage and highest business-critical symbols first.

## Execution Workflow

1. Run adapter check per symbol:
   - `POST /api/v1/backfill/adapter-check`
2. Run chunked recovery windows from newest to oldest:
   - `POST /api/v1/backfill/window`
   - default chunk: 7 days
3. Validate KPI after each pass:
   - `ohlcv_bar` counts by venue/symbol
   - `raw_tick` recency by venue/symbol
4. Repeat only failing symbols until coverage converges or provider history limits are hit.

## Automation

Use:

- `scripts/session/per-symbol-recovery.sh`

Config:

- `HOST` (default `http://localhost:8110`)
- `LOOKBACK_DAYS` (default `90`)
- `CHUNK_DAYS` (default `7`)

## Provider-Specific Notes

- Capital: smaller per-request windows are required to avoid `error.invalid.max.daterange`.
- Coinbase: product fallback candidates (`-USD`/`-USDC`) must be attempted for symbol compatibility.
- Oanda: occasional network timeout/HTTP 504 requires retry passes; continuity can still converge across repeated runs.
