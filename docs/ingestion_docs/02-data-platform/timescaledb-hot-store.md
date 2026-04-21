# TimescaleDB Hot Store (EPIC-05)

## Objective

Persist finalized 1-minute bars to a TimescaleDB hypertable as hot operational truth.

## Runtime Service

- Compose service: `timescaledb`
- Init SQL path: `infra/timescaledb/init/001_init_hot_store.sql`

## Hot Table

`ohlcv_bar` fields:
- `venue`
- `canonical_symbol`
- `timeframe`
- `bucket_start`
- `open`, `high`, `low`, `close`
- `volume`
- `trade_count`
- `last_event_ts`
- timestamps (`inserted_at`, `updated_at`)

Primary key:
- `(venue, canonical_symbol, timeframe, bucket_start)`

## Upsert Policy

- Upsert by primary key.
- Preserve extreme values with `GREATEST/LEAST`.
- Always advance `close` and `last_event_ts` on newer state.

## Data Permanence Alignment

- No deletion policies enabled by default.
- Schema and workflows are designed for non-destructive operation.
