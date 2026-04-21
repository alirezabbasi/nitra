# EPIC-08 Implementation Log

## Story 08.1: ClickHouse Cold Schema

Completed:
- Added ClickHouse initialization SQL:
  - `bars_hist`
  - `archive_loaded_manifest`
- Added Timescale checkpoint table for loader progress:
  - `cold_loader_checkpoint`

## Story 08.2: Cold Loader Pipeline

Completed:
- Added `cold_loader` service:
  - reads manifests from Timescale
  - reads Parquet from lakehouse
  - inserts rows into ClickHouse
  - marks manifests as loaded
  - advances checkpoint

## Story 08.3: Query API Hot/Cold Split

Completed:
- Implemented `query_api` service with routes:
  - `/health`
  - `/v1/bars/hot`
  - `/v1/bars/cold`
- Added Timescale and ClickHouse client wiring.

## Story 08.4: Runtime and SDLC Wiring

Completed:
- Added Dockerfiles for `cold_loader` and `query_api`.
- Added compose services for:
  - `clickhouse`
  - `cold-loader`
  - `query-api`
- Added EPIC-08 test pack under `tests/epic-08`.

## Verification

- `cargo fmt --all`
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo test --workspace`
- `./tests/epic-08/run.sh`
- `docker compose config`
