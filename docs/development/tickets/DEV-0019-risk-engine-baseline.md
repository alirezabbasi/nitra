# DEV-0019: Deterministic Risk Engine Baseline

## Status

Done (2026-04-26)

## Summary

Implement first runnable deterministic `risk-engine` runtime in Rust to enforce baseline policy checks and publish explicit risk decisions.

## Scope

- Replace `services/risk-engine` sleep scaffold with runnable Rust service.
- Consume configurable risk input stream (baseline wired to `structure.snapshot.v1`).
- Evaluate deterministic risk policy checks:
  - min confidence threshold
  - max notional cap
  - max drawdown threshold
  - kill-switch fail-closed rule
- Emit:
  - `decision.risk_checked.v1`
  - `ops.policy_violation.v1`
- Persist risk state and decision log to Timescale.
- Preserve replay-safe idempotency with `processed_message_ledger`.

## Non-Goals

- Full portfolio engine integration.
- Broker account margin and compliance adapters.
- Execution gateway order lifecycle wiring.

## Architecture Alignment

- HLD data flow where risk evaluates tradability before execution.
- LLD service catalog section 10 (Risk Engine responsibilities and outputs).
- Section 5.1 compliance (deterministic core runtime in Rust).

## Acceptance Criteria

- Runnable risk service in compose (no scaffold sleep command).
- Deterministic policy decisions emitted to `decision.risk_checked.v1`.
- Policy violations emitted to `ops.policy_violation.v1`.
- Risk state and decision audit rows persisted in Timescale.
- Ticket test pack and policy gates pass.

## Implementation Notes

- Added Rust runtime in `services/risk-engine`:
  - `Cargo.toml`
  - `src/main.rs`
  - deterministic risk evaluator and baseline policy model
  - supports signal-style input and structure-snapshot bootstrap input
- Updated `services/risk-engine/Dockerfile` to compiled Rust runtime.
- Updated compose env/runtime contract for risk topics and policy knobs.
- Added Kafka topic bootstrap entries for risk decision and violation streams.
- Added Timescale migration `008_risk_state.sql` (`risk_state`, `risk_decision_log`).
- Added `tests/dev-0019/run.sh` and `make test-dev-0019`.

## Verification Evidence

- `CARGO_TARGET_DIR=/tmp/nitra-risk-engine-target cargo check --offline --manifest-path services/risk-engine/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-risk-engine-target cargo test --offline --manifest-path services/risk-engine/Cargo.toml`
- `tests/dev-0019/run.sh`
- `make enforce-section-5-1`
