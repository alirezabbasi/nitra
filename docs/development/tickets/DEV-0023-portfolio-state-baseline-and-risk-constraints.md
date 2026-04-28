# DEV-0023: Portfolio-State Baseline and Richer Risk Constraints

## Status

Done (2026-04-28)

## Summary

Implement deterministic `portfolio-engine` baseline and wire `risk-engine` to enforce portfolio-aware constraints.

## Scope

- Add runnable Rust `portfolio-engine` service.
- Consume fill events and persist deterministic portfolio state.
- Emit `portfolio.snapshot.v1` updates.
- Persist baseline portfolio contracts:
  - `portfolio_position_state`
  - `portfolio_account_state`
  - `portfolio_fill_log`
- Extend risk policy with portfolio-aware constraints:
  - symbol exposure cap
  - portfolio gross exposure cap
  - minimum available equity

## Non-Goals

- Full PnL accounting and mark-to-market valuation.
- Multi-account strategy allocation model.
- Portfolio rebalancing automation.

## Acceptance Criteria

- Portfolio engine runs in compose and persists deterministic state.
- `portfolio.snapshot.v1` topic is registered and emitted.
- Risk engine enforces richer portfolio-aware constraints with explicit violations.
- Migration, tests, docs, and policy/session gates pass.

## Implementation Notes

- Added:
  - `services/portfolio-engine/Cargo.toml`
  - `services/portfolio-engine/Dockerfile`
  - `services/portfolio-engine/src/main.rs`
  - `infra/timescaledb/init/011_portfolio_state.sql`
  - `tests/dev-0023/run.sh`
- Updated:
  - `services/risk-engine/src/main.rs`
  - `docker-compose.yml`
  - `infra/kafka/topics.csv`
  - `Makefile`

## Verification Evidence

- `cargo fmt --manifest-path services/portfolio-engine/Cargo.toml`
- `cargo fmt --manifest-path services/risk-engine/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-portfolio-risk-target cargo check --offline --manifest-path services/portfolio-engine/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-portfolio-risk-target cargo test --offline --manifest-path services/portfolio-engine/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-portfolio-risk-target cargo check --offline --manifest-path services/risk-engine/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-portfolio-risk-target cargo test --offline --manifest-path services/risk-engine/Cargo.toml`
- `tests/dev-0023/run.sh`
- `make enforce-section-5-1`
- `make session-bootstrap`
