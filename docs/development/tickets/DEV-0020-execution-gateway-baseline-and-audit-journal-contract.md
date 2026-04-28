# DEV-0020: Execution Gateway Baseline and Audit/Journal Persistence Contract

## Status

Done (2026-04-28)

## Summary

Implement first runnable deterministic `execution-gateway` runtime in Rust and introduce the project-wide baseline persistence contract for execution/audit journaling.

## Scope

- Replace `services/execution-gateway` scaffold with runnable Rust service.
- Consume approved risk intents from `decision.risk_checked.v1`.
- Implement deterministic execution state transitions baseline:
  - reject (not approved / hold / zero notional)
  - submitted
  - filled
  - reconciliation issue (high-notional signal)
- Emit execution topics:
  - `exec.order_submitted.v1`
  - `exec.order_updated.v1`
  - `exec.fill_received.v1`
  - `exec.reconciliation_issue.v1`
- Add project-wide execution/audit persistence contract in Timescale:
  - `execution_order_journal`
  - `audit_event_log`
- Preserve idempotent processing with `processed_message_ledger`.

## Non-Goals

- Real broker API routing and acknowledgment adapters.
- Full OMS amend/cancel + partial-fill lifecycle completion.
- Portfolio/position accounting integration.

## Architecture Alignment

- LLD section 12 execution gateway contracts and section 15 audit/observability persistence direction.
- HLD deterministic risk->execution flow with auditable trace requirements.
- Section 5.1 deterministic core runtime mandate (Rust).

## Acceptance Criteria

- Service runnable in compose (no scaffold `sleep`).
- Consumes `decision.risk_checked.v1` and emits execution topics.
- Persists execution order journal and audit event rows.
- Replay-safe idempotency behavior is enforced.
- Ticket test pack and section-5.1 hard gate pass.

## Implementation Notes

- Added runtime:
  - `services/execution-gateway/Cargo.toml`
  - `services/execution-gateway/src/main.rs`
- Added deterministic baseline runtime path with explicit event emission and DB persistence.
- Updated `services/execution-gateway/Dockerfile` to compiled binary image.
- Updated compose runtime env contract for execution topics + dry-run knobs.
- Added Kafka topic bootstrap entries for execution streams.
- Added migration `infra/timescaledb/init/009_execution_audit_journal.sql`.
- Added `tests/dev-0020/run.sh` and `make test-dev-0020`.

## Verification Evidence

- `CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo check --offline --manifest-path services/execution-gateway/Cargo.toml`
- `CARGO_TARGET_DIR=/tmp/nitra-execution-gateway-target cargo test --offline --manifest-path services/execution-gateway/Cargo.toml`
- `tests/dev-0020/run.sh`
- `make test-dev-0020`
- `make enforce-section-5-1`
