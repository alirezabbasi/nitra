# Backfill Backlog Cleanup and Drain Policy

## Purpose

Define a safe, practical policy to normalize backfill/replay backlog without destructive data operations.

## Scope

Applies to ingestion recovery pipeline components:

- `gap-detection`
- `backfill-worker`
- `replay-controller`
- runtime tables: `gap_log`, `backfill_jobs`, `replay_audit`, `ohlcv_bar`

## Safety Rules

1. No deletion-based cleanup
- Do not delete rows from `gap_log`, `backfill_jobs`, or `replay_audit`.
- Normalize backlog using status transitions only.

2. Registry-authoritative cleanup
- Cleanup targets only `(venue, canonical_symbol)` pairs not present in canonical registry.
- Unknown markets are terminally marked and excluded from replay churn.

3. One-time cleanup must be auditable
- Execute via versioned SQL script in `docs/development/debugging/sql/`.
- Capture before/after metrics in `docs/development/debugging/reports/`.

## Standard Drain Process

1. Capture before snapshot
- Unknown-market rows in `backfill_jobs`.
- Status distribution in `backfill_jobs` and `replay_audit`.
- 90-day coverage debt by registry market.

2. Run safe one-time cleanup SQL
- Script: `docs/development/debugging/sql/2026-04-26-one-time-cleanup-legacy-unknown-market-backfill.sql`
- Status-only updates:
  - `backfill_jobs` unknown markets -> `failed_unknown_market`
  - `replay_audit` linked queued/partial rows -> `failed` with cleanup error note
  - `gap_log` unknown markets -> `ignored_unknown_market`

3. Capture after snapshot
- Re-run same before queries.
- Confirm unknown-market `queued` rows are reduced to zero.

4. Continue normal drain
- Keep backpressure enabled.
- Keep registry guardrails fail-closed.
- Prioritize valid queued ranges oldest-first.

## Operational Exit Criteria

Backlog is considered normalized when all are true:

- unknown-market rows in `queued`/`running`/`partial` are `0`,
- queue growth is bounded and not caused by invalid market pairs,
- coverage debt trend decreases for registry-valid symbols,
- open/backfill_queued unknown-market gaps remain `0`.

## Notes

- Coverage debt will not improve from cleanup alone; cleanup removes invalid workload so valid symbols can progress faster.
- Any future registry change should be followed by a small audit query for newly unknown legacy rows.
