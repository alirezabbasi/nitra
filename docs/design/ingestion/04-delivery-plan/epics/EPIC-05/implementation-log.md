# EPIC-05 Implementation Log

## Story 05.1: Deterministic 1m Aggregation

Completed:
- Implemented bar engine consuming normalized quote events.
- Added deterministic minute-bucket aggregator with OHLC/trade_count logic.
- Added finalization logic on bucket rollover.
- Added handling for late-event dropping.

## Story 05.2: Timescale Hot Persistence

Completed:
- Added TimescaleDB service to Docker Compose.
- Added init migration for `bars_1m_recent` hypertable.
- Added upsert writer from bar engine to TimescaleDB.
- Added bar event publishing to `bar.1m` topic.

## Story 05.3: SDLC and Runtime Wiring

Completed:
- Added bar-engine Dockerfile and compose service.
- Added EPIC-05 environment variables and Makefile log/test targets.
- Added EPIC-05 test pack under `tests/epic-05`.

## Verification

- `cargo fmt --all`
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo test --workspace`
- `./tests/epic-05/run.sh`
- `docker compose config`
