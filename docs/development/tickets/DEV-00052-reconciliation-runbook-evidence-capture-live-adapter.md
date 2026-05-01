# DEV-00052: Reconciliation/Runbook Evidence Capture for Live Adapter Behavior

## Goal

Expand operator-facing reconciliation/runbook evidence capture so live adapter failures and recovery actions are bound to auditable runbook execution context.

## Scope

- Persist runbook-linked reconciliation evidence snapshots for:
  - `execution_command_log`
  - execution-domain `audit_event_log`
  - `incident_evidence_bundle`
- Extend runbook execution input with optional linkage identifiers:
  - `order_id`
  - `correlation_id`
  - `lookback_minutes`
- Return and persist `evidence_summary` for runbook executions.
- Expose ops metric for evidence snapshot activity over the last 24 hours.

## Implementation Notes

- Runtime implementation:
  - `services/charting/app.py`
- Migration contract:
  - `infra/timescaledb/init/018_control_panel_reconciliation_evidence.sql`
- Verification:
  - `tests/dev-0052/run.sh`
  - `make test-dev-0052`

## Acceptance

- Runbook execution captures linked adapter/reconciliation evidence when identifiers are provided.
- Evidence snapshots are persisted in `control_panel_reconciliation_evidence`.
- Ops module exposes `evidence_snapshots_24h` metric.
- Verification gate passes.

## Definition of Done

A ticket is complete only when all conditions below are true:

- Acceptance criteria are fully met without unresolved scope gaps.
- Required implementation is merged in this repository and aligned with HLD/LLD constraints.
- Tests are added/updated for the scope and passing evidence is recorded.
- Operational/documentation artifacts for the scope are updated (runbooks/contracts/docs as applicable).
- Execution tracking and memory artifacts are synchronized (`KANBAN`, `CURRENT_STATE`, `SESSION_LEDGER`).
- Residual risks, assumptions, and follow-up actions are explicitly documented.

## Verification Evidence

- `make test-dev-0052` pass
- `make enforce-section-5-1` pass
- `make session-bootstrap` pass
