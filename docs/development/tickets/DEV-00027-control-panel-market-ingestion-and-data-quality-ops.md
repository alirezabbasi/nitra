# DEV-00027: Control Panel Market Ingestion and Data Quality Operations Center

## Status

Done (2026-04-29)

## Summary

Create operator surfaces for connector health, ingestion continuity, backfill orchestration, and data-quality diagnostics.

## Scope

- Connector health matrix (venue status, lag, heartbeat, error rate).
- Coverage and gap monitoring by venue/symbol/timeframe.
- Backfill job control surface (queue, retries, priority, outcomes).
- Replay audit viewer and deterministic execution trace drilldown.
- Quick actions for safe recovery workflows.

## Non-Goals

- Re-implement charting module internals.
- Free-form destructive maintenance actions.

## Acceptance Criteria

- Operators can identify and triage ingestion failures quickly.
- Coverage/gap state is visible and actionable.
- Replay/backfill controls are observable with audit logs.

## Verification

- API contract tests for health/coverage/backfill views.
- End-to-end operator workflow test for gap-to-recovery path.
- `tests/dev-00027/run.sh`
