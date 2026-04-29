# DEV-00037: Structure-Engine Production Deterministic Hardening

## Status

Done (2026-04-29)

## Summary

Upgrade structure-engine from baseline to production-grade deterministic state-machine behavior with strict transition invariants.

## Scope

- Formalize transition table for pullback/minor/major states.
- Add invariant guards against illegal transitions.
- Harden out-of-order/duplicate bar handling under replay.
- Persist transition reason codes for downstream explainability.

## Non-Goals

- New trading strategy logic.
- ML-based structural inference.

## Acceptance Criteria

- No illegal transition paths are reachable.
- Duplicate/out-of-order replay does not corrupt state.
- Transition reasons are emitted and persisted for every state change.

## Verification

- Deterministic transition property tests.
- Replay/regression fixtures with expected state snapshots.

## Delivery Evidence

- Formalized invariant guards and blocked illegal transitions in runtime:
  - `has_illegal_transition(...)` checks phase/trend validity, event-flag consistency, and counter/time monotonicity.
- Hardened replay handling for duplicate/out-of-order bars:
  - bars with `bucket_start <= last_bucket_start` are fail-closed ignored (no state mutation).
- Persisted transition reason codes:
  - `structure_state.last_transition_reason` runtime wiring + migration `012_structure_transition_reason.sql`.
  - emitted `transition_reason` plus persisted `last_transition_reason` for every accepted state update.
- Added verification pack:
  - `tests/dev-0037/run.sh`
  - `make test-dev-0037`
