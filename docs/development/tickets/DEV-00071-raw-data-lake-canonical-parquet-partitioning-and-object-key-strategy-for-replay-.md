# DEV-00071: Raw Data Lake - canonical Parquet partitioning and object-key strategy for replay-grade raw archives.

## Status

Done

## Goal

Define and deliver: Raw Data Lake - canonical Parquet partitioning and object-key strategy for replay-grade raw archives.

## Scope

- Implementation changes required by this ticket.
- Test coverage and verification evidence for this ticket.
- Documentation and operational updates needed for closeout.

## Acceptance Criteria

- Behavior/contract described in the goal is implemented.
- Deterministic and regression tests are added/updated.
- Relevant docs/runbooks are updated.
- Kanban and memory artifacts are synchronized with final status.

## Definition of Done

A ticket is complete only when all conditions below are true:

- Acceptance Criteria are fully met without unresolved scope gaps.
- Required implementation is merged in this repository and aligned with HLD/LLD constraints.
- Tests are added/updated for the scope and passing evidence is recorded.
- Operational/documentation artifacts for the scope are updated (runbooks/contracts/docs as applicable).
- Execution tracking and memory artifacts are synchronized (`KANBAN`, `CURRENT_STATE`, `SESSION_LEDGER`).
- Residual risks, assumptions, and follow-up actions are explicitly documented.

## Verification

- Run the relevant `make test-*` target(s) for this scope.
- `make enforce-section-5-1`
- `make session-bootstrap`

## Notes

- This ticket file was generated to restore ticket-registry integrity from `KANBAN.md`.
- Implemented canonical partitioned parquet object-key strategy in normalization runtime via deterministic `raw_lake_object_manifest` projection.
- Implemented replay-grade provenance persistence per object window (`source_topic/partition`, min/max offsets, first/last event timestamps, row count).
- Added control-panel ingestion visibility for recent raw-lake manifest objects and 24h object count metric.
- Verification target added: `make test-dev-0071`.
