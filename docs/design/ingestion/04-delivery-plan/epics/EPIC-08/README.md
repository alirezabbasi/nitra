# EPIC-08: ClickHouse Cold Analytics

## Scope
- Load historical events/bars from lake into ClickHouse.
- Move heavy analytics off Timescale.

## Deliverables
- ClickHouse DDL and load pipeline.
- Cold query API surface.
- Benchmarks for analytical workloads.

## Acceptance
- Operational DB no longer carries heavy historical scan load.

## Commit Slices
1. `feat(clickhouse): add warehouse schema and loaders`
2. `feat(api): split hot/cold query paths`
