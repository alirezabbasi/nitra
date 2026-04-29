# Feature Service (DEV-00038)

## Purpose

Materialize deterministic, point-in-time-safe feature snapshots for downstream signal/risk stages.

## Inputs

- Kafka topic: `structure.snapshot.v1`

## Outputs

- Kafka topic: `features.snapshot.v1`
- TimescaleDB table: `feature_snapshot`

## Determinism and PIT Contract

- Features are computed from:
  - current structure snapshot payload,
  - previous persisted feature state only.
- No lookahead joins are allowed.
- Identical input sequence must yield identical feature vectors.

## Lineage Contract

Each feature snapshot includes lineage fields sufficient for replay/forensics:

- `source_topic`
- `source_partition`
- `source_offset`
- `window.previous_bucket_start`
- `window.current_bucket_start`
- `schema_version`

## Baseline Feature Set (`dev-00038.v1`)

- `ret_1`
- `bar_range`
- `bar_body`
- `range_body_ratio`
- `ewma_return`
- `trend_score`
- `phase_pullback`
- `transition_reason`

## Validation

- `tests/dev-0038/run.sh`
- unit tests under `tests/dev-0038/unit`
