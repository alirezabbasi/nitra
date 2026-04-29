# DEV-00038: Feature Service Deterministic Baseline and Point-in-Time Integrity

## Status

Done (2026-04-29)

## Summary

Implement deterministic feature computation layer with strict point-in-time correctness and lineage metadata.

## Scope

- Implement core deterministic feature transforms from bars + structure.
- Enforce no-lookahead point-in-time joins.
- Persist feature snapshots with lineage (source offsets/window/version).
- Add online/offline consistency checks for deterministic feature outputs.

## Non-Goals

- Full feature platform rollout beyond baseline scope.
- Model training orchestration changes.

## Acceptance Criteria

- Feature outputs are reproducible from same inputs.
- Point-in-time leakage tests pass.
- Lineage metadata is queryable for every feature snapshot.

## Verification

- Feature correctness tests.
- PIT anti-leak tests.
- Lineage persistence checks.

## Delivery Evidence

- Added Python `feature-service` deterministic baseline runtime:
  - `services/feature-service/app.py`
  - `services/feature-service/Dockerfile`
- Added feature persistence contract and lineage query support:
  - `infra/timescaledb/init/013_feature_snapshot.sql`
- Added runtime/infra wiring:
  - `docker-compose.yml` (`feature-service`)
  - `infra/kafka/topics.csv` (`features.snapshot.v1`)
  - `policy/technology-allocation.yaml` (`feature_service` now runtime-active + compliant)
- Added deterministic/PIT verification pack:
  - `tests/dev-0038/run.sh`
  - `tests/dev-0038/unit/test_feature_logic.py`
  - `make test-dev-0038`
