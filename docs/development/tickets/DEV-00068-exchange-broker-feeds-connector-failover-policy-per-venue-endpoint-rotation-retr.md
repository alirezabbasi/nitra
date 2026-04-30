# DEV-00068: Exchange/Broker Feeds - connector failover policy per venue (endpoint rotation, retry tiers, circuit-open thresholds).

## Status

Done (2026-05-01)

## Goal

Define and deliver: Exchange/Broker Feeds - connector failover policy per venue (endpoint rotation, retry tiers, circuit-open thresholds).

## Scope

- Implementation changes required by this ticket.
- Test coverage and verification evidence for this ticket.
- Documentation and operational updates needed for closeout.

## Acceptance Criteria

- Behavior/contract described in the goal is implemented.
- Deterministic and regression tests are added/updated.
- Relevant docs/runbooks are updated.
- Kanban and memory artifacts are synchronized with final status.

## Verification

- `make test-dev-0068`
- `make enforce-section-5-1`
- `make session-bootstrap`

## Delivered Artifacts

- `services/charting/app.py`
  - failover policy persistence contract (`control_panel_ingestion_failover_policy`)
  - ingestion module failover policy/runtime payload
  - guarded update endpoint `POST /api/v1/control-panel/ingestion/failover-policy`
- `docs/design/ingestion/02-data-platform/broker-1-connector.md` failover contract section.
