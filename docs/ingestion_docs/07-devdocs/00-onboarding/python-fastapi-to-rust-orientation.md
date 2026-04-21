# Python/FastAPI to Rust Orientation

This guide is for developers coming from Python + FastAPI to the BarsFP Rust codebase.

## Mental Model Translation

- FastAPI app modules -> Rust service crates in `services/*`.
- Pydantic/data models -> shared Rust structs/enums in `crates/domain` and `crates/contracts`.
- Background workers/Celery tasks -> always-on Rust worker services (`normalizer`, `bar_engine`, `gap_engine`, etc.).
- API routers -> `axum::Router` in service `main.rs` (for `query_api`, and observability routes in `risk_gateway` and `oms`).
- Settings class + env vars -> per-service `*Config` struct built from environment.
- Dependency injection -> explicit function parameters and typed structs.

## Where to Start Reading

1. Workspace root: `Cargo.toml` (all crates and services).
2. Shared data contracts:
   - `crates/domain/src/lib.rs`
   - `crates/contracts/src/lib.rs`
3. Runtime orchestration: `docker-compose.yml`.
4. Service entrypoints: `services/*/src/main.rs`.

## "Web Service" vs "Worker" in This Repo

- HTTP API service:
  - `services/query_api/src/main.rs`
- Worker/stream processors (Kafka/DB loop, no public HTTP):
  - `connector`, `normalizer`, `bar_engine`, `gap_engine`, `backfill_worker`, `archive_worker`, `cold_loader`
- Mixed services (worker + small internal HTTP endpoints for health/metrics):
  - `risk_gateway`, `oms`

## Rust Patterns You Will See Repeatedly

- `#[tokio::main] async fn main()` for async runtime startup.
- `run_once(...)` inside retry loop for resilient workers.
- `Result<T>` with `anyhow` for error propagation.
- Strong typed contracts passed through `Envelope<T>` message payloads.
- `tokio-postgres` for TimescaleDB access and `rdkafka` for Redpanda topics.

## Practical Navigation Tip

When you inspect any service, read in this order:

1. `*Config` struct (which env vars drive behavior)
2. `main()` (what starts)
3. `run_once()` / main processing loop
4. input parsing + output publish functions
5. DB persistence/idempotency helpers
6. tests at bottom of file

