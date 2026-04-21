# EPIC-21 Implementation Log

## Story 21.1: Market Event Entity Schema

Completed:
- Added TimescaleDB entity schema for:
  - `raw_tick`
  - `book_event`
  - `trade_print`
- Added hypertable setup and primary indexes for event-time scans.
- Added hot-bar canonical table rename support:
  - primary hot bar table is now `ohlcv_bar`
  - compatibility view `bars_1m_recent` points to `ohlcv_bar`

## Story 21.2: Multi-Venue Persistence Path

Completed:
- Added normalizer-side classification and persistence for raw market entities.
- Added idempotent inserts keyed by `message_id` with `ON CONFLICT DO NOTHING`.
- Added classification coverage for OANDA/CAPITAL/COINBASE payload patterns.

## Story 21.3: Table Rename Propagation

Completed:
- Rewired hot-bar read/write paths from `bars_1m_recent` to `ohlcv_bar` in:
  - bar engine
  - gap engine
  - archive worker
  - query API
- Updated runtime defaults (`ARCHIVE_STREAM_NAME`) to `ohlcv_bar`.

## Verification

- `cargo fmt --all`
- `cargo test -p barsfp-normalizer`
- `cargo test -p barsfp-bar-engine`
- `cargo test -p barsfp-gap-engine`
- `cargo test -p barsfp-archive-worker`
- `cargo test -p barsfp-query-api`
- `docker compose config`
- `tests/epic-21/run.sh`
