# EPIC-03 Implementation Log

## Story 03.1: Broker Adapter Service

Completed:
- Implemented async connector runtime in `services/connector`.
- Added config model from environment variables.
- Added `mock` mode for local/dev signal generation.
- Added `oanda` mode for streaming line-delimited JSON ingestion.
- Added `capital` mode for authenticated polling ingestion.
- Added `coinbase` mode for websocket ingestion with channel subscriptions.
- Added reconnect loop with configurable backoff.
- Added periodic connector health event publishing.

## Story 03.2: Stream Publishing and Containerization

Completed:
- Added Redpanda publish path with `rdkafka` producer.
- Added service Dockerfile:
  - `services/connector/Dockerfile`
- Added compose service wiring for `oanda-adapter`, `capital-adapter`, and `coinbase-adapter`.
- Added `.dockerignore` to reduce build context noise.

## Story 03.3: Documentation and Runability

Completed:
- Added connector architecture/runtime document.
- Updated `.env.example` with OANDA/CAPITAL/COINBASE adapter settings.
- Updated `Makefile` with adapter-specific logs targets.

## Verification

- `cargo fmt --all`
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo test --workspace`
- `docker compose config`
