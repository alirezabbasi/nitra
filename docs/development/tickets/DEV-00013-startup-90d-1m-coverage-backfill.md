# DEV-00013: Startup 90-Day 1m Coverage Enforcement and Missing-Only Backfill

## Status

Implemented in code (runtime validation evidence collection in progress)

## Summary

Enforce business requirement that charting-ready `1m` candles always cover the rolling 90-day window (`now` back to `now - 90 days`) for every active instrument.

On service startup, the system must validate coverage in `ohlcv_bar` and automatically fetch missing historical data from broker APIs.

Architectural ownership note:
- 90-day coverage enforcement/backfill is ingestion-owned and must run independently of charting service availability.
- Charting is a consumer/visualizer and optional trigger surface, not the owner of mandatory historical recovery.
- Runtime rule: effective coverage window cannot be below 90 days (minimum floor enforced in `gap-detection`).

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
  - includes persistent recovery loop for queue durability:
    - re-enqueues stale/orphaned `queued` jobs back to `replay.commands`,
    - auto-resets stale `running` jobs back to `queued`,
    - tracks `enqueue_count` / `last_enqueued_at` metadata in `backfill_jobs`.
  - deterministic drain tuning:
    - queued recovery now applies stale-only gating (`BACKFILL_QUEUED_STALE_SECS`) and oldest-first scheduling,
    - avoids broad queue churn by requiring stale replay-audit evidence before re-enqueue.
    - replay-queue backpressure now dynamically scales (and hard-stops) recovery re-enqueue when `replay_audit.queued` exceeds configurable watermarks, preventing backlog amplification under sustained load.
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
  - supports safe in-process parallelism via `REPLAY_WORKER_COUNT` (multiple Kafka consumers under same group, partition-level scaling).
- Implemented replay-controller venue-history fallback adapters:
  - when replay range remains incomplete after `raw_tick` rebuild, fetches venue candles from `oanda`, `coinbase` (with public fallback), or `capital`.
  - upserts fetched bars into `ohlcv_bar` and re-evaluates range completeness before assigning final replay/backfill status.
- Charting runtime now derives non-`1m` timeframe responses from `1m` backfilled storage, ensuring 90-day view continuity across timeframe switches once `1m` coverage is complete.

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
