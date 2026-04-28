# DEV-00021: Execution Gateway Broker-Venue Adapter Layer

## Status

Done (2026-04-28)

## Summary

Implement the broker-venue adapter baseline in `execution-gateway` for live submit/amend/cancel routing and broker ack/fill ingestion.

## Scope

- Extend `execution-gateway` to consume:
  - `decision.risk_checked.v1`
  - `exec.order_command.v1`
  - `broker.execution.ack.v1`
- Add live adapter route contract for:
  - submit
  - amend
  - cancel
- Keep deterministic dry-run fallback behavior for local validation.
- Extend execution persistence contracts:
  - `execution_order_journal` (`broker_order_id`, `state_version`)
  - `execution_command_log`
- Keep idempotent replay-safe semantics via `processed_message_ledger`.

## Non-Goals

- Broker-specific authentication/session lifecycle orchestration.
- Advanced retry/backoff circuit-breaker policy.
- Portfolio accounting and PnL updates.

## Architecture Alignment

- LLD section 12 execution gateway contract (single OMS boundary, broker ack/fill lifecycle handling).
- LLD section 15 audit/journal traceability requirements.
- HLD deterministic risk->execution path with auditable state transitions.

## Acceptance Criteria

- Runtime handles live submit/amend/cancel adapter calls.
- Runtime consumes broker ack/fill events and updates journal deterministically.
- Command decisions are persisted and auditable.
- Kafka/compose/schema contracts are updated for new adapter streams/env.
- Tests and section 5.1 hard gate pass.

## Implementation Notes

- Updated:
  - `services/execution-gateway/src/main.rs`
  - `services/execution-gateway/Cargo.toml`
  - `docker-compose.yml`
  - `infra/kafka/topics.csv`
  - `infra/timescaledb/init/010_execution_broker_adapter.sql`
- Added:
  - `tests/dev-0021/run.sh`
  - `make test-dev-0021`

## Verification Evidence

- `cargo fmt --manifest-path services/execution-gateway/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo check --offline --manifest-path services/execution-gateway/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo test --offline --manifest-path services/execution-gateway/Cargo.toml`
- `tests/dev-0021/run.sh`
- `make enforce-section-5-1`
- `make session-bootstrap`
