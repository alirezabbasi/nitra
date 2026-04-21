# Source Review: `../barflow`

## What Was Reviewed

- Full `../barflow/docs` tree.
- Deep focus on:
  - `Automated Financial market trading system.md`.
  - `Multi-broker market data load.md`.
- Supporting docs used to preserve operational lessons:
  - `PGImprovementPlan/*`
  - `roadmap/*`
  - `runbooks/*`
  - `techstack/*`
  - `v1-pipeline/*`

## Key Findings to Keep

1. System must be risk-first, not indicator-first.
2. Raw events are ground truth; candles are derived.
3. Canonical normalization is non-negotiable in multi-broker systems.
4. Gap detection + precise backfill are first-class production requirements.
5. Idempotency, replay, and reconciliation are core reliability controls.
6. Release gates (research, engineering, risk, ops) must block unsafe rollout.

## Key Gaps to Fix in Revamp

1. Legacy implementation centers on Python + Redis streams; target is Rust + Redpanda.
2. Cold analytics separation should be explicit early (ClickHouse + lakehouse).
3. Hot/cold/lake contracts need stricter ownership and lifecycle documentation.
4. Ops maturity needs stronger service-level objectives tied to alert policies.
5. Governance artifacts (ADRs, rollout gates, change controls) need tighter integration with delivery workflow.

## Revamp Direction

`barsfp` becomes the production-grade multi-broker data and trading-control platform with:

- Rust services for ingestion, normalization, aggregation, risk gateway, execution core.
- Redpanda as durable event backbone.
- TimescaleDB for 90-day hot operational truth.
- ClickHouse for deep historical analytics and replay-oriented scans.
- MinIO/S3 Parquet archive as immutable event lake.
- Grafana stack for metrics, logs, traces, dashboards, and alerting.
