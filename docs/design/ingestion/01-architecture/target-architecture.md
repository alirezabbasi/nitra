# Target Architecture (Bars Flow Plus)

## Architecture Principles

1. Event-first design: source events are immutable truth.
2. Deterministic derivation: bars and risk state must be reproducible.
3. Risk-before-execution: no bypass path.
4. Operability by default: every service exposes health, readiness, metrics.
5. Replaceable internals behind stable contracts.

## Core Runtime Domains

1. Ingestion Domain (Rust)
- Broker connectors (WS/REST).
- Heartbeat/reconnect/rate-limit control.
- Raw event publishing to Redpanda.

2. Canonicalization Domain (Rust)
- Normalize broker payloads into canonical schema.
- Enrich with symbol/session metadata.
- Emit canonical tick/trade/quote streams.

3. Aggregation Domain (Rust)
- Build deterministic 1s/1m bars from canonical events.
- Emit bar-close and quality signals.
- Persist hot bars to TimescaleDB.

4. Integrity Domain (Rust)
- Coverage tracker (tail + internal gaps).
- Backfill scheduler + worker.
- Replay and rebuild pipeline.

5. Execution + Risk Domain (Rust)
- Strategy runtime adapter (versioned artifacts).
- Pre-trade risk gateway.
- OMS state machine and reconciliation.
- Kill-switch + circuit-breaker controls.

6. Data Plane Storage
- Hot: TimescaleDB (90 days).
- Cold analytics: ClickHouse.
- Archive: MinIO/S3 Parquet lake.

7. Control Plane
- Config service + feature flags.
- Strategy registry metadata.
- Operator API.

8. Observability Plane
- Prometheus (metrics), Loki (logs), Tempo (traces), Grafana (dashboards).

## End-to-End Flow

1. Connector -> `raw.market.<venue>`
2. Normalizer -> `normalized.<event_type>.<asset_class>`
3. Bar builder -> `bar.1s`, `bar.1m`, higher-timeframe derivations
4. Gap engine -> `gap.events`
5. Backfill worker -> targeted replay -> rebuild
6. Hot persistence -> TimescaleDB
7. Cold ETL -> ClickHouse
8. Archive writer -> Parquet to MinIO
9. Query + operator APIs consume hot/cold stores with strict read contracts

## Environment Strategy

- `dev`: rapid iteration, synthetic and paper data.
- `paper`: production-like controls and SLO enforcement.
- `prod`: restricted rollout only after gates pass.
