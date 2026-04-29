# DEV-00042: Portfolio Authoritative Reconciliation and State Invariants

## Status

Open

## Summary

Upgrade portfolio engine to authoritative reconciled state with explicit invariants against execution/fill history.

## Scope

- Add strict position/account invariants (quantity, cash, equity consistency).
- Reconcile portfolio state against execution journal and fill log.
- Emit drift/break alerts with deterministic reason taxonomy.
- Add repair-safe workflows for reconciliation exceptions.

## Non-Goals

- New PnL model innovation.
- External accounting integration.

## Acceptance Criteria

- Portfolio state reconciles deterministically with fills/journal.
- Drift conditions are detectable, auditable, and actionable.
- Invariant breaches are fail-closed with explicit diagnostics.

## Verification

- Invariant property tests.
- Reconciliation regression fixtures.
- Drift alert emission checks.
