# DEV-00064: Next Roadmap Slice - Feature Platform Contract and Shadow Readiness

## Status

Planned

## Goal

Define and execute the first post-control-panel implementation slice focused on deterministic feature-platform readiness without changing live trading decisions.

## Scope

- Freeze the feature event contract between `structure-engine` outputs and feature-service inputs for shadow mode.
- Define point-in-time parity checks between offline feature recomputation and live stream snapshots.
- Add shadow-readiness observability fields for feature freshness, missing lineage, and deterministic replay equivalence.
- Keep live risk/execution decision path unchanged (advisory-only shadow integration).

## Acceptance Criteria

- A versioned contract spec for shadow feature snapshots is documented and linked in design docs.
- A deterministic parity-check workflow is defined for replay vs. live feature snapshots.
- A verification pack exists as `tests/dev-0064/run.sh` and is executable via `make test-dev-0064`.
- Kanban and memory artifacts reflect `DEV-00064` as the next active implementation slice.

## Verification

- `make test-dev-0064`
- `make enforce-section-5-1`
- `make session-bootstrap`

## Notes

- This ticket is the concrete roadmap conversion artifact requested after `DEV-00063` closure.
- Implementation should be split into small follow-up commits preserving test/doc traceability.
