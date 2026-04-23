# EPIC-15: Async I/O and Bulk Data Plane Efficiency

## Scope
- Isolate blocking file/parquet work from async runtime.
- Optimize cold-loader and archival throughput with batch-oriented paths.

## Deliverables
- Blocking I/O isolation strategy (`spawn_blocking` + bounded workers).
- ClickHouse bulk-ingest tuning and chunking policy.
- Backpressure and queue safety controls with observability hooks.

## Acceptance
- Archive/load pipeline meets throughput SLO without async starvation signals.

## Commit Slices
1. `feat(io): isolate blocking parquet/fs operations from async runtime`
2. `perf(loader): add batch ingest and backpressure controls`
