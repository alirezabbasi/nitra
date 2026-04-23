# EPIC-04 Implementation Log

## Story 04.1: Canonical Normalization Service

Completed:
- Implemented normalizer runtime consuming raw events from Redpanda.
- Added conversion from `Envelope<RawMarketEvent>` to `Envelope<CanonicalEvent>`.
- Added quote extraction and validation logic.

## Story 04.2: Symbol Registry

Completed:
- Added versioned symbol registry file:
  - `infra/symbols/registry.v1.json`
- Added in-memory indexed lookup by `(venue, broker_symbol)`.
- Added passthrough toggle (default fail-closed).

## Story 04.3: Runtime and DevOps Wiring

Completed:
- Added normalizer Dockerfile.
- Added compose service for normalizer.
- Added normalizer env vars and Makefile logs target.
- Added EPIC-04 test pack under `tests/epic-04`.

## Verification

- `cargo fmt --all`
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo test --workspace`
- `./tests/epic-04/run.sh`
- `docker compose config`
