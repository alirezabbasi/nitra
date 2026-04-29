# DEV-00037: Structure-Engine Production Deterministic Hardening

## Status

Open

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
