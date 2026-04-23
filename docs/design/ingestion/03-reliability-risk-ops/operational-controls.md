# Reliability, Risk, and Ops Controls

## Non-Negotiables

1. At-least-once processing with idempotent writes.
2. No silent drops.
3. Gap detection covers tail and internal intervals.
4. Backfill fetches missing-only ranges.
5. Pre-trade risk checks are non-bypassable.
6. Reconciliation runs continuously.

## SLO Baseline

- Ingestion lag p95 < 2s during active sessions.
- Hot coverage >= 99.95% for open-market minutes.
- Gap backlog resolved within 15 minutes p95.
- Readiness status must be green before execution enablement.

## Alert Families

- Data staleness and stream lag.
- Gap backlog growth.
- Backfill retry/DLQ growth.
- Risk-engine unavailable.
- Order reject anomalies.
- Reconciliation mismatch incidents.

## Runbook Pack (Required Before Prod)

- Broker disconnect recovery.
- Stale feed diagnosis and replay.
- Gap repair failure handling.
- Hot/cold/lake divergence response.
- Risk breach and kill-switch handling.
- Rollback and service restoration drill.

Paper and micro-live runbooks:
- `paper-rollout-runbook.md`
- `micro-live-checklist-and-rollback.md`
- `emergency-procedures.md`

## Release Gates

1. Research gate
2. Engineering gate
3. Risk gate
4. Ops gate

No gate pass, no production promotion.
