# Service LLD Guide

## Service Set

- `connector` (adapter runtime)
- `normalizer`
- `bar_engine`
- `gap_engine`
- `backfill_worker`
- `archive_worker`
- `cold_loader`
- `risk_gateway`
- `oms`
- `query_api`
- `chart-ui`

## Per-Service Documentation Standard

Each service change should document:

- responsibility and boundaries,
- input topics/tables,
- output topics/tables,
- failure/retry behavior,
- config variables,
- test strategy,
- observability signals.

Service-specific details should be maintained in subject docs under `docs/02-data-platform/` and `docs/03-reliability-risk-ops/`.

## Codebase Skeleton

- `rust-codebase-skeleton.md`: end-to-end map of workspace layout, shared crates, service entrypoints, core function locations, and HTTP endpoints.
- `chart-ui-service.md`: charting web service boundaries, runtime topology, and proxy/data-flow contract.
