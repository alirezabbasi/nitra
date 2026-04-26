# Current State Snapshot

Last updated: 2026-04-26

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
- Live validation audit (2026-04-24) confirmed Coinbase feed rows are still produced by mock ingestion source (`nitra.market_ingestion.mock`) and backfill pipeline is dominated by `failed_no_source_data`.
- Registered ingestion bug records `BUG-00005` (mock Coinbase feed) and `BUG-00006` (startup backfill source-depth failure mode).
- Removed runtime mock ingestion generation and replaced `market-ingestion` with venue-sourced fetch paths (OANDA/Capital/Coinbase) plus fail-closed `CONNECTOR_MODE=mock` rejection and anti-mock test guardrails.
- Completed chart UX parity upgrade ticket `DEV-00015`: realtime return, jump-to-time/index, zoom/scroll locks, range/crosshair metadata, history lazy loading, snapshot export, locale/timezone/format controls, and interaction-density/margin tuning.
- Implemented replay-controller venue-history fallback adapters (`oanda`/`coinbase`/`capital`) so replay ranges can fetch broker candles when `raw_tick` depth is insufficient.
- Hardened charting venue adapters for transient network errors and numeric payload variance; added `POST /api/v1/backfill/adapter-check` live probe endpoint.
- Updated compose/env contracts and dev test packs (`tests/dev-0013`, `tests/dev-0014`) for replay-history and adapter-hardening coverage.
- Backfill range execution priority updated to newest-first so recent continuity is restored before deep-history windows.
- Added gap-detection periodic coverage scanner to continuously detect latest-90d `1m` gaps and emit deterministic backfill requests.
- Added charting explicit-range backfill endpoint (`/api/v1/backfill/window`) plus read-only coverage observability endpoints (`/api/v1/coverage/status`, `/api/v1/coverage/metrics`).
- Updated charting timeframe APIs so non-`1m` candles are derived from `1m` coverage, enabling full-history timeframe availability after `1m` backfill completion.
- Backfill queue-drain hardening implemented:
  - stale-only queued recovery gating (`BACKFILL_QUEUED_STALE_SECS`) with deterministic oldest-first re-enqueue order.
  - replay-controller scaled with safe multi-worker consumer mode (`REPLAY_WORKER_COUNT`) for partition-level parallel drain.
- Live operational pass added replay-queue backpressure gate:
  - `replay.commands` expanded to 8 partitions.
  - `backfill-worker` now applies queued-watermark backpressure (`BACKFILL_REPLAY_QUEUE_*`) so recovery re-enqueue is hard-stopped when replay backlog is above high watermark.
  - live slope check now shows replay queued backlog declining under backpressure-enabled settings.
- Charting drawing workflow upgraded with TradingView-style annotation features: grouped drawing tool memory, cursor/navigate draw-exit mode, auto-retrigger drawing lifecycle, brush styling controls, custom measure/long/short overlays, undo/redo history, and local layout/drawing persistence.
- Charting UI redesigned from crowded top-row controls to a TradingView-style left icon sidebar plus grouped drawing control panel for faster annotation workflows and cleaner primary header.
- Live runtime evidence capture completed on 2026-04-26 for `DEV-00013`/`DEV-00014`:
  - SQL status snapshots captured for `backfill_jobs`, `replay_audit`, `gap_log`.
  - coverage metrics/status endpoints captured from charting.
  - adapter-check probes captured explicit external-network error diagnostics (`Network is unreachable`, `timed out`, `Temporary failure in name resolution`).

### Current

- `DEV-00013` closed with live runtime evidence and explicit surfaced error-state diagnostics.
- `DEV-00014` closed with live adapter-check and coverage evidence.
- Section 5.1 enforcement active (policy-as-code + hard gates) with migration batch completed.

### Next

1. Implement deterministic structure-engine runtime baseline.
2. Implement deterministic risk-engine and execution-gateway runtime baselines.
3. Open a focused adapter-network resilience ticket to reduce external DNS/connectivity failure impact.

### Risks/Blocks

- Risk of architecture drift toward ingestion-only progress.
- Risk of context drift if memory files are not updated at session close.
- Open decision: priority ordering between replay controller and structure-engine first slice.
- Open dependency: adapter correctness is implemented and observable, but success rate depends on stable outbound network/DNS in runtime.
- External risk: Coinbase Exchange candles endpoint may return 403 in some runtimes; fallback route health must be monitored.
- Runtime restart needed to clear historical mock-origin rows from operational validation windows.

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
