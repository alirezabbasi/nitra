# EPIC-12 Implementation Log

## Story 12.1: Explicit Commit and Ack Lifecycle

Completed:
- Disabled `enable.auto.commit` on all stream consumers handling critical topics.
- Added explicit synchronous offset commit after successful processing/publish paths.
- Added explicit commit for deterministic drop paths (invalid/empty/unparseable payloads) to prevent poison-pill loops.
- Standardized per-service commit helper with contextual commit-failure error messages.

Services updated:
- `services/normalizer`
- `services/bar_engine`
- `services/gap_engine`
- `services/backfill_worker`
- `services/risk_gateway`
- `services/oms`

## Story 12.2: Test and SDLC Wiring for EPIC-12

Completed:
- Added EPIC-12 test pack under `tests/epic-12/`.
- Added Make target `test-epic-12` and included EPIC-12 in `tests/run-all.sh`.

## Story 12.3: Idempotency Ledger and Replay Guards (Phase 1)

Completed:
- Added Timescale migration `infra/timescaledb/init/007_processed_message_ledger.sql`.
- Added `Envelope.message_id` replay guard checks in:
  - `services/bar_engine`
  - `services/risk_gateway`
  - `services/oms`
- Added ledger write after successful side effects/publish and before offset commit.
- Updated stream reliability docs with manual commit + replay guard contract.

## Story 12.4: Idempotency Ledger and Replay Guards (Phase 2)

Completed:
- Extended replay guards to remaining ingest/repair consumers:
  - `services/normalizer`
  - `services/gap_engine`
  - `services/backfill_worker`
- Added Timescale access in `normalizer` and persisted dedup decisions using `Envelope.message_id`.
- Standardized duplicate handling behavior:
  - duplicate -> skip side effects -> commit offset
  - first-seen -> process side effects -> write ledger row -> commit offset

## Story 12.5: Integration Replay Drill (Phase 3)

Completed:
- Added phase-3 integration script:
  - `tests/epic-12/run-phase3-integration.sh`
- Implemented live duplicate injection across stream inputs and asserted single side effects:
  - `execution.orders` -> `risk_gateway` ledger + `risk_decisions`
  - `risk.events` -> `oms` ledger + `orders_recent`
  - `raw.market.oanda` -> `normalizer` ledger
  - `bar.1m` -> `gap_engine` ledger
  - `gap.events` -> `backfill_worker` ledger + `backfill_jobs`
- Added optional execution gate in `tests/epic-12/run.sh` via `EPIC12_PHASE3_INTEGRATION=1`.
- Added make target `test-epic-12-phase3` for explicit SDLC execution.

## Verification

- `cargo fmt --all`
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo test --workspace`
- `./tests/epic-12/run.sh`
- `EPIC12_PHASE3_INTEGRATION=1 ./tests/epic-12/run.sh`
