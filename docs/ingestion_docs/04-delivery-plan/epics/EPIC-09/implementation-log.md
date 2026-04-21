# EPIC-09 Implementation Log

## Story 09.1: Risk Gateway Controls

Completed:
- Implemented `risk_gateway` service with:
  - intake from `execution.orders`
  - non-bypassable decision emission to `risk.events`
  - pre-trade controls (kill switch, quantity, per-order notional)
  - post-trade control (daily filled notional)
- Added Timescale persistence table:
  - `risk_decisions`
- Added shared contracts for:
  - `ExecutionOrderEvent`
  - `OrderIntent`
  - `RiskDecisionEvent`

## Story 09.2: OMS Lifecycle and Reconciliation

Completed:
- Implemented `oms` service with:
  - decision-driven order submission path (allow/reject)
  - idempotent submission keyed by `command_id`
  - fill handling keyed by `venue_fill_id`
  - order state publication to `execution.orders`
  - periodic reconciliation loop and `flag_and_hold` policy
- Added Timescale persistence tables:
  - `orders_recent`
  - `fills_recent`
  - `oms_reconciliation_log`

## Story 09.3: Runtime, Tests, and Documentation

Completed:
- Added Dockerfiles and compose wiring for:
  - `risk-gateway`
  - `oms`
- Added EPIC-09 env variables and Make targets.
- Added step test pack under `tests/epic-09/`.
- Added EPIC risk/OMS controls documentation in `docs/03-reliability-risk-ops/`.

## Verification

- `cargo fmt --all`
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo test --workspace`
- `./tests/epic-09/run.sh`
- `docker compose config`
