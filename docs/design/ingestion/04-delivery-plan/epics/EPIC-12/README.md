# EPIC-12: Stream Correctness and Delivery Guarantees

## Scope
- Replace auto-commit consumer behavior with explicit commit flow after successful side effects.
- Enforce replay-safe and idempotent processing across stream consumers.

## Deliverables
- Consumer commit/ack policy with failure and retry semantics.
- Idempotency key contract and persistence strategy.
- Replay and duplicate-handling verification suite.

## Acceptance
- Injected failures and replay runs produce no silent loss and no duplicate side effects.

## Commit Slices
1. `feat(stream): add explicit commit and ack lifecycle`
2. `feat(stream): add idempotency ledger and replay guards`
3. `test(stream): add duplicate replay integration drill and evidence`
