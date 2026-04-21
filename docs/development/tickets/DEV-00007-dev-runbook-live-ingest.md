# DEV-00007: Development Runbook for Live Market Ingestion

## Status

Done

## Summary

Create the operator/developer runbook for starting NITRA ingestion in dev and validating live market data flow safely.

## Scope

- Document startup, bootstrap, health checks, validation queries, and safe stop procedures.
- Include live-feed enablement checklist with environment prerequisites.
- Include rollback/fallback steps for failed ingestion sessions.

## Hard Exclusions

- No production-only operational procedures mixed into baseline dev runbook.
- No references to deprecated BarsFP-only commands unless explicitly mapped to NITRA equivalents.

## Deliverables

1. Dev runbook document under `docs/development/` or ingestion docs.
2. Validation checklist for raw -> normalized -> persisted data path.
3. Troubleshooting section for common failure modes.

## Acceptance Criteria

- New contributor can run ingestion from docs only.
- Live data ingestion validation steps are explicit and reproducible.
- Safe stop/restart procedure preserves data and aligns with no-deletion policy.

## Evidence

- Runbook: `docs/development/DEV-00007-live-ingestion-runbook.md`
- Validation checklist included for raw -> normalized -> persisted path
- Troubleshooting and safe stop/restart/rollback sections included
