# Where Are We

Last updated: 2026-04-24

## Completed

- `DEV-00001..DEV-00007` ingestion baseline is complete.
- Development operating system and memory system are in place.
- Project-wide documentation system has been unified and cross-links cleaned.

## Recent

- Latest delivery commit for baseline scope: `f51c5f5`.
- HLD Section 5 coverage reviewed and synchronized into roadmap.
- `DEV-00010` completed: `market-ingestion` connector runtime migrated to Rust.
- `DEV-00011` completed: `market-normalization` runtime migrated to Rust.
- `DEV-00012` completed: bar/gap/backfill deterministic runtimes migrated to Rust.
- Charting fix session completed: corrected live candle merge logic, improved live-fit behavior, and moved market selection to header dropdowns.
- HLD/LLD updated with mandatory startup 90-day `1m` historical coverage policy for all active instruments.
- `DEV-00013` created to implement startup coverage audit + missing-only broker backfill.
- `DEV-00013` runtime baseline implemented: startup 90-day coverage scan in `gap-detection`, gap persistence/events, and chunked backfill job/replay orchestration in `backfill-worker`.
- `DEV-00013` replay execution step implemented: `replay-controller` now consumes `replay.commands` and updates `ohlcv_bar` plus backfill/replay status tables.
- `DEV-00014` implementation added in charting backfill path: Capital history adapter, Coinbase fallback route, and session-aware FX weekend continuity policy.

## Current

- Section 5.1 hard-gate enforcement active with deterministic-core migration batch completed.
- `DEV-00013` is in progress with replay execution wired; remaining work is source-history depth where replay ranges have no `raw_tick` data.
- `DEV-00014` is in progress pending live adapter validation hardening.

## Next

1. Complete `DEV-00014` live validation and close adapter/runtime edge cases.
2. Implement broker-history adapters in replay path to fulfill ranges beyond currently available `raw_tick` depth.
3. Implement deterministic structure-engine runtime baseline.
4. Implement deterministic risk/execution runtime baselines.

## Risks/Blocks

- Context drift if session close memory updates are skipped.
- Delivery risk shifted to deterministic engine implementation depth (structure/risk/execution).
- Open dependency: replay execution is wired, but 90-day completion still depends on source history availability/adapters.
- Runtime dependency: Coinbase venue history can be blocked on Exchange endpoint; fallback endpoint behavior must be monitored.

## Section 5.1 Compliance Snapshot

- Hard gate status: active
- Deterministic-core Python services: none
- Blocked policy: no net-new deterministic Python scope
- Current migration tickets: none
