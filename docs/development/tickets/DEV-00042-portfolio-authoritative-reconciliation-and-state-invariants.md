# DEV-00042: Portfolio Authoritative Reconciliation and State Invariants

## Status

Done (2026-04-29)

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

## Delivery Evidence

- Added authoritative reconciliation pass to `services/portfolio-engine/src/main.rs`:
  - computes position/account exposure consistency,
  - validates gross/net/equity invariants with deterministic reason taxonomy.
- Added persistence and evidence contract:
  - `portfolio_reconciliation_log` migration `infra/timescaledb/init/016_portfolio_reconciliation_log.sql`.
- Added drift/break alert emission:
  - deterministic `portfolio_reconciliation_drift` issue payloads on reconciliation failures.
- Added runtime controls:
  - `PORTFOLIO_MAX_GROSS_EXPOSURE_NOTIONAL`
  - `PORTFOLIO_MAX_ABS_NET_EXPOSURE_NOTIONAL`
  - `PORTFOLIO_MIN_EQUITY`
  - `PORTFOLIO_DRIFT_TOPIC`
- Added verification pack:
  - `tests/dev-0042/run.sh`
  - `make test-dev-0042`
