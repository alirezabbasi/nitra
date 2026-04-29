# DEV-00038: Feature Service Deterministic Baseline and Point-in-Time Integrity

## Status

Open

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
