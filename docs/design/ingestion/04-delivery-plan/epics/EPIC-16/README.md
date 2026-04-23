# EPIC-16: Storage and Query Path Performance

## Scope
- Tune Timescale and ClickHouse data models for production query profiles.
- Harden hot/cold query routing and indexing/partition strategies.

## Deliverables
- Timescale retention/compression/continuous-aggregate tuning pack.
- ClickHouse partition/order key and query-shape optimization pack.
- Query API path and cache strategy review for p95/p99 stability.

## Acceptance
- Operational and analytical query latency SLOs are met under load tests.

## Commit Slices
1. `feat(storage): tune hot-store retention/compression/aggregates`
2. `feat(query): optimize cold-store schema and query routing`
