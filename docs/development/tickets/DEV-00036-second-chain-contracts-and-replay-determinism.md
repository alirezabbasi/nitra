# DEV-00036: Second-Chain Contracts and Replay Determinism

## Status

Open

## Summary

Freeze and enforce canonical contracts across structure/features/signal/risk/execution/portfolio/journal to eliminate schema drift and replay ambiguity.

## Scope

- Define canonical schema contracts and required fields for:
  - `structure.snapshot.v1`
  - `features.snapshot.v1`
  - `signal.scored.v1` (or approved equivalent)
  - `decision.risk_checked.v1`
  - `exec.order_*`
  - `portfolio.snapshot.v1`
  - journal/audit domain events
- Add runtime schema validation at producer/consumer edges.
- Define strict ordering/idempotency requirements per topic.
- Add deterministic replay equivalence checks (same input => same output/state).

## Non-Goals

- Feature logic expansion.
- Strategy tuning or model improvements.

## Acceptance Criteria

- Contract tests exist for every chain edge.
- Invalid payloads fail closed with explicit reason.
- Replay equivalence tests pass on representative fixtures.

## Verification

- Contract/schema test suite across all second-chain topics.
- Replay determinism test pack with byte/stable-state comparison.
