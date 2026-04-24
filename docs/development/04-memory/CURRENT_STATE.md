# Current State Snapshot

Last updated: 2026-04-24

## Where Are We Snapshot

### Completed

- Ingestion baseline delivery completed for `DEV-00001..DEV-00007`.
- Development operating system and persistent memory framework established under `docs/development/`.
- HLD Section 5 coverage assessment completed and mapped to roadmap statuses.
- Documentation system unified with canonical entrypoints and de-duplicated delivery artifacts.

### Recent

- Committed baseline delivery set: `f51c5f5`.
- Reorganized `docs/development/` into governance, roadmap, execution, delivery, and memory sections.
- Added project-wide docs entrypoint and ruleset-level "Where are we?" requirement.
- Completed `DEV-00010` cutover: `market-ingestion` moved from Python to Rust runtime.
- Completed `DEV-00011` cutover: `market-normalization` moved from Python to Rust runtime.
- Completed `DEV-00012` cutover: bar/gap/backfill services moved from Python to Rust runtime.
- Charting stabilization patch applied for live candle integrity, auto-fit behavior, and header-based venue/instrument selection.
- Charting selector upgraded to searchable input and timeframe switching restored with 1m-derived fallback for `5m/15m/1h` when native bars are absent.
- Added formal architecture requirement: startup must guarantee rolling 90-day `1m` coverage in `ohlcv_bar` for all active instruments.
- Registered `DEV-00013` to implement deterministic startup coverage audit + missing-only broker backfill.
- Implemented `replay-controller` executor for `replay.commands` with deterministic `ohlcv_bar` rebuild and backfill/audit status transitions.
- Implemented charting-side venue-history adapter expansion (`DEV-00014` in progress): Capital REST historical fetch, Coinbase fallback route, and session-aware continuity policy for FX weekend closure.

### Current

- `DEV-00013` is in progress with replay execution now wired (`gap-detection` + `backfill-worker` + `replay-controller`).
- `DEV-00014` is in progress with implementation complete in code; live validation and adapter hardening continue.
- Section 5.1 enforcement active (policy-as-code + hard gates) with migration batch completed.

### Next

1. Validate `DEV-00014` end-to-end in live runtime and close remaining external adapter/network issues.
2. Implement broker-history adapters in replay controller path for ranges where `raw_tick` source coverage is missing.
3. Implement deterministic structure-engine runtime baseline.
4. Implement deterministic risk-engine and execution-gateway runtime baselines.

### Risks/Blocks

- Risk of architecture drift toward ingestion-only progress.
- Risk of context drift if memory files are not updated at session close.
- Open decision: priority ordering between replay controller and structure-engine first slice.
- Open dependency: broker-history fulfillment still depends on source history adapters beyond current `raw_tick`-backed replay execution.
- External risk: Coinbase Exchange candles endpoint may return 403 in some runtimes; fallback route health must be monitored.

## Program status

- Overall project phase: transition from ingestion baseline to core deterministic engine implementation.
- Active focus: project-wide roadmap alignment and next ticket batch definition.

## Architecture coverage (HLD Section 5)

- Implemented: ingestion connectors, Kafka backbone, Timescale baseline schema.
- Partial: normalization/replay path, raw data lake archival, MLflow/research infra, observability basics.
- Scaffold only: structure engine, risk engine, execution gateway, llm-analyst.
- Not started: feature platform (Feast), portfolio engine, full online inference layer (Ray Serve).

## Section 5.1 Compliance Snapshot

- Enforcement mode: hard-gate now (`make enforce-section-5-1`).
- Gate runner: local scripts + Make targets (CI-ready).
- Deterministic-core non-compliant migrating services:
  - none
- Blocked rule active: no net-new deterministic Python feature scope.
