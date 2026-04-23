# DEV-00010: Rust Migration — Market Ingestion Connectors

## Status

Done (2026-04-23)

## Summary

Migrate `market-ingestion` connector runtime from Python to Rust in line with HLD Section 5.1 and ADR-0001 deterministic-core policy.

## Scope

- Replace Python connector runtime with Rust implementation.
- Preserve existing topic and envelope contracts.
- Preserve health telemetry semantics.

## Non-Goals

- Strategy/risk/portfolio feature expansion.
- Contract-breaking topic changes.

## Enforcement Context

- Previous state: `non_compliant_migrating` under waiver `WVR-0001` (retired by cutover).
- No net-new deterministic connector features in Python.

## Acceptance Criteria

- Rust connector publishes equivalent raw/health payload contracts.
- Policy gate marks service `compliant` after cutover.
- Existing ingestion verification tests pass with migration updates.

## Implementation Notes

- Replaced Python runtime in `services/market-ingestion` with Rust service (`Cargo.toml`, `src/main.rs`).
- Preserved connector env contract (`INGESTION_*`, `KAFKA_BROKERS`, `CONNECTOR_MODE`) and payload/envelope shape.
- Updated connector Docker image to compiled Rust binary runtime.
- Updated Compose wiring for `market-ingestion`, `market-ingestion-capital`, `market-ingestion-coinbase`.
- Updated policy manifest state for `market_ingestion_connectors` to `compliant`.
- Updated verification script `tests/dev-00005/run.sh` to validate Rust connector compile path.

## Verification Evidence

- `make enforce-section-5-1`
- `tests/dev-00005/run.sh`
- `tests/dev-0010/run.sh`
