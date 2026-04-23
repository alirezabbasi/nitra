# DEV-00011: Rust Migration — Market Normalization and Replay

## Status

Done (2026-04-23)

## Summary

Migrate `market-normalization` and replay control path from Python to Rust for deterministic-core compliance.

## Scope

- Re-implement normalization and replay lifecycle in Rust.
- Preserve canonical symbol and schema contract behavior.
- Preserve idempotency and deduplication invariants.

## Non-Goals

- New analytics features.
- Data contract version changes unless separately approved.

## Enforcement Context

- Previous state: `non_compliant_migrating` under waiver `WVR-0002` (retired by cutover).
- No net-new deterministic normalization features in Python.

## Acceptance Criteria

- Rust normalization/replay path reaches contract parity.
- Replay and idempotency tests pass with Rust implementation.
- Policy gate marks service `compliant` after cutover.

## Implementation Notes

- Replaced Python runtime in `services/market-normalization` with Rust service (`Cargo.toml`, `src/main.rs`).
- Preserved env and contract behavior (`NORMALIZER_*`, `DATABASE_URL`, envelope and normalized payload shape).
- Preserved idempotency guard semantics with `processed_message_ledger` checks and `ON CONFLICT DO NOTHING`.
- Preserved manual commit processing semantics (`enable.auto.commit=false` + explicit commit).
- Updated Docker image to compiled Rust binary runtime.
- Updated Compose registry mount path for runtime binary deployment.
- Updated policy manifest state for `market_normalization_replay` to `compliant`.
- Updated `tests/dev-00005/run.sh` and `tests/dev-00006/run.sh` for Rust validation.

## Verification Evidence

- `cargo check --manifest-path services/market-normalization/Cargo.toml`
- `tests/dev-00005/run.sh`
- `tests/dev-00006/run.sh`
- `DEV00006_INTEGRATION=1 tests/dev-00006/run.sh`
- `tests/dev-0010/run.sh`
- `make enforce-section-5-1`
