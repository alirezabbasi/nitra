# DEV-0018: Deterministic Structure Engine Baseline

## Status

Done (2026-04-26)

## Summary

Implement the first runnable deterministic `structure-engine` runtime in Rust so market-structure state is no longer a scaffold service.

## Scope

- Replace `services/structure-engine` sleep scaffold with runnable Rust service.
- Consume `bar.1m` events and maintain deterministic per-market structure state.
- Emit structure event streams:
  - `structure.snapshot.v1`
  - `structure.pullback.v1`
  - `structure.minor_confirmed.v1`
  - `structure.major_confirmed.v1`
- Persist single-source-of-truth state into Timescale (`structure_state`).
- Keep replay-safe processing semantics via `processed_message_ledger`.

## Non-Goals

- Full strategy-grade market structure model calibration.
- Risk/execution integration.
- LLM-assisted interpretation paths.

## Architecture Alignment

- HLD section 9 data flow step 7/8 (structure consumes bars and emits structure snapshot).
- LLD service catalog section 5 (deterministic structure engine responsibilities and outputs).
- Section 5.1 compliance (deterministic core runtime remains Rust).

## Acceptance Criteria

- Service is runnable in compose without `sleep` placeholder.
- Input consumed from `bar.1m` with explicit consumer group.
- Deterministic state transitions produce structure outputs on dedicated topics.
- Structure state is persisted and upserted per `(venue, canonical_symbol, timeframe)`.
- Baseline tests and policy checks pass.

## Implementation Notes

- Added Rust runtime in `services/structure-engine`:
  - `Cargo.toml`
  - `src/main.rs`
  - deterministic state machine baseline (trend/phase/objective + pullback/confirmation signals)
  - explicit idempotency guard via `processed_message_ledger`
- Updated `services/structure-engine/Dockerfile` to compiled binary runtime.
- Updated compose contract (`structure-engine`) with structure topic env vars and removed scaffold command.
- Added Kafka topic bootstrap entries for structure outputs.
- Added Timescale init migration for `structure_state` table.
- Added verification pack `tests/dev-0018/run.sh` and Make target `test-dev-0018`.

## Verification Evidence

- `cargo test --manifest-path services/structure-engine/Cargo.toml`
- `cargo check --manifest-path services/structure-engine/Cargo.toml`
- `tests/dev-0018/run.sh`
- `make enforce-section-5-1`
