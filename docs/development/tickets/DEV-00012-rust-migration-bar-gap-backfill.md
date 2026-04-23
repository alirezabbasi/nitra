# DEV-00012: Rust Migration — Bar Aggregation, Gap Detection, Backfill Controller

## Status

Done (2026-04-23)

## Summary

Migrate deterministic aggregation and recovery services (`bar-aggregation`, `gap-detection`, `backfill-worker`) from Python to Rust.

## Scope

- Replace all three deterministic services with Rust implementations.
- Preserve topic contracts and data safety semantics.
- Preserve gap/backfill behavior and replay triggers.

## Non-Goals

- New strategy or UI features.
- Non-deterministic processing additions.

## Enforcement Context

- Previous state: `non_compliant_migrating` under waiver `WVR-0003` (retired by cutover).
- No net-new deterministic scope in Python for these services.

## Acceptance Criteria

- Rust services replace Python runtime behavior with contract parity.
- Existing integration tests for ingestion path pass after migration updates.
- Policy gate marks this component `compliant` after cutover.

## Implementation Notes

- Replaced Python runtimes with Rust services:
  - `services/bar-aggregation` (`Cargo.toml`, `src/main.rs`)
  - `services/gap-detection` (`Cargo.toml`, `src/main.rs`)
  - `services/backfill-worker` (`Cargo.toml`, `src/main.rs`)
- Preserved topic contracts (`normalized.quote.fx` -> `bar.1m` -> `gap.events` -> `replay.commands`).
- Preserved replay-safe ledger semantics (`processed_message_ledger`, `ON CONFLICT DO NOTHING`).
- Preserved manual commit behavior (`enable.auto.commit=false` + explicit commit).
- Updated Docker images for all three services to compiled Rust runtime.
- Updated Compose service runtime mounts to binary-oriented deployment.
- Updated policy manifest state for `bar_gap_backfill` to `compliant`.
- Added migration test pack `tests/dev-0012` and updated existing dev checks.

## Verification Evidence

- `cargo check --manifest-path services/bar-aggregation/Cargo.toml`
- `cargo check --manifest-path services/gap-detection/Cargo.toml`
- `cargo check --manifest-path services/backfill-worker/Cargo.toml`
- `tests/dev-00005/run.sh`
- `tests/dev-00006/run.sh`
- `tests/dev-0010/run.sh`
- `tests/dev-0012/run.sh`
- `DEV0012_INTEGRATION=1 tests/dev-0012/run.sh`
- `make enforce-section-5-1`
