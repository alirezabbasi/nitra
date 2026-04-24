# DEV-00013: Startup 90-Day 1m Coverage Enforcement and Missing-Only Backfill

## Status

In Progress (replay-controller executor implemented; full 90-day completion still depends on source history depth / broker-history adapters)

## Summary

Enforce business requirement that charting-ready `1m` candles always cover the rolling 90-day window (`now` back to `now - 90 days`) for every active instrument.

On service startup, the system must validate coverage in `ohlcv_bar` and automatically fetch missing historical data from broker APIs.

## Scope

- Define active-instrument set used for startup coverage checks.
- Implement startup coverage audit for `ohlcv_bar` at `1m` resolution.
- Detect and materialize missing intervals in deterministic chunks.
- Trigger broker historical fetch for missing ranges only.
- Rebuild/persist missing `1m` bars deterministically.
- Expose readiness/status so operators can see coverage progress.

## Non-Goals

- Changing charting UI behavior.
- Introducing non-deterministic/heuristic bar reconstruction.
- Replacing existing live ingestion flow.

## Architecture Alignment

- HLD Section 6.2: startup coverage enforcement requirement.
- LLD Service Catalog Sections 3 and 4: startup audit + missing-only backfill behavior.
- Section 5.1 compliance: deterministic core implementation in Rust.

## Acceptance Criteria

- On startup, each active `venue + symbol` is checked for complete 90-day `1m` continuity.
- If gaps exist, missing-only backfill jobs are generated and executed.
- `ohlcv_bar` reaches full 90-day `1m` coverage (or a surfaced explicit error state with reason).
- Readiness is not `healthy` while required startup coverage remains incomplete.
- Idempotent reruns do not duplicate bars or replay work unnecessarily.

## Implementation Notes (Planned)

- Implemented startup coverage scan in `services/gap-detection`:
  - loads active instruments from symbol registry + DB signal.
  - checks rolling 90-day `1m` coverage window.
  - records/publishes missing ranges into `gap_log` + `gap.events`.
- Implemented deterministic backfill orchestration in `services/backfill-worker`:
  - processes startup/open gaps and stream gaps.
  - chunks missing ranges (`BACKFILL_FETCH_CHUNK_MINUTES`).
  - persists `backfill_jobs` + `replay_audit`.
  - emits replay commands with broker-history fetch metadata.
- Added runtime schema support for coverage/gap/backfill/replay tables:
  - `infra/timescaledb/init/004_gap_backfill_runtime.sql`.
  - runtime `CREATE TABLE IF NOT EXISTS` safety in gap/backfill services.
- Added compose/runtime controls:
  - `GAP_STARTUP_SCAN_ENABLED`, `GAP_STARTUP_COVERAGE_DAYS`, `GAP_SYMBOL_REGISTRY_PATH`.
  - `BACKFILL_STARTUP_PROCESS_OPEN_GAPS`, `BACKFILL_FETCH_CHUNK_MINUTES`.
- Implemented replay-controller executor:
  - consumes `replay.commands`.
  - rebuilds `1m` bars from replay ranges using available `raw_tick` source data.
  - updates `backfill_jobs`, `replay_audit`, and resolves covered gaps in `gap_log`.
- Remaining dependency:
  - broker-history adapters are still required where `raw_tick` does not already contain the requested 90-day range.

## Verification Plan

- Unit tests:
  - coverage window gap detection
  - chunk planner correctness
  - idempotent merge/write behavior
- Integration tests:
  - startup with full data => no backfill
  - startup with partial data => backfill to completion
  - startup with broker failure => degraded/failed readiness with explicit error
- Operational checks:
  - SQL verification for 90-day continuity
  - readiness endpoint/state reflects actual coverage status

## Deliverables

- Deterministic runtime updates in Rust services (bar/gap/backfill path).
- Test pack for `DEV-00013` under `tests/`.
- Runbook update for startup historical coverage verification.
- Memory and execution board updates upon completion.
