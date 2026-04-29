# DEV-00036: Second-Chain Contracts and Replay Determinism

## Status

Done (2026-04-29)

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

## Delivery Evidence

- Added canonical second-chain contract baseline:
  - `docs/design/ingestion/07-devdocs/03-lld-data-model/second-chain-contracts-and-replay-determinism.md`
  - `docs/design/ingestion/07-devdocs/03-lld-data-model/contracts/second-chain/*.schema.json`
- Added deterministic replay equivalence unit tests:
  - `services/structure-engine/src/main.rs` (`replay_sequence_is_deterministic`)
  - `services/risk-engine/src/main.rs` (`risk_policy_evaluation_is_deterministic`)
- Added verification pack:
  - `tests/dev-0036/run.sh`
  - `make test-dev-0036`
