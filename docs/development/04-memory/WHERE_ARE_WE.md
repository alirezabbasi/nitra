# Where Are We

Last updated: 2026-04-26

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
- `DEV-00013` replay path upgraded with venue-history fallback adapters (`oanda`/`coinbase`/`capital`) for ranges that remain incomplete after raw-tick replay.
- `DEV-00014` adapter hardening completed with retry behavior improvements and live probe endpoint `POST /api/v1/backfill/adapter-check`.
- Backfill execution priority updated to recent-first (`newest -> oldest`) for missing ranges.
- Added gap-detection periodic coverage scanner plus explicit charting window endpoint (`/api/v1/backfill/window`) for automatic and operator-driven gap recovery.
- Charting non-`1m` timeframes now derive from `1m` backfilled history, improving full-range availability after 90d coverage rebuild.
- Captured live runtime evidence for `DEV-00013`/`DEV-00014` on 2026-04-26 (`backfill_jobs`, `replay_audit`, `gap_log`, coverage metrics, adapter-check diagnostics) and closed both tickets.
- `DEV-0018` completed: deterministic `structure-engine` baseline implemented in Rust (`bar.1m` consumer, structure topics, persisted `structure_state`, idempotent ledger semantics).

## Current

- Section 5.1 hard-gate enforcement active with deterministic-core migration batch completed.
- `DEV-00013` is closed with live runtime evidence and explicit surfaced external-network adapter error diagnostics.
- `DEV-00014` is closed with live runtime adapter-check and coverage evidence.
- `DEV-0018` is closed with deterministic runtime baseline, compose wiring, topic contracts, and test pack (`dev-0018`).

## Next

1. Implement deterministic risk/execution runtime baselines.
2. Add project-wide audit/journal event persistence contract.
3. Add follow-up operability ticket for adapter-network resilience (timeouts/name-resolution handling and retry/backoff tuning).

## Risks/Blocks

- Context drift if session close memory updates are skipped.
- Delivery risk shifted to deterministic engine implementation depth (structure/risk/execution).
- Open dependency: stable outbound network path is still required for end-to-end adapter success despite explicit error surfacing.
- Runtime dependency: Coinbase venue history can be blocked on Exchange endpoint; fallback endpoint behavior must be monitored.

## Section 5.1 Compliance Snapshot

- Hard gate status: active
- Deterministic-core Python services: none
- Blocked policy: no net-new deterministic Python scope
- Current migration tickets: none
