# Where Are We

Last updated: 2026-04-28

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
- `DEV-0019` completed: deterministic `risk-engine` baseline implemented in Rust (policy checks, `decision.risk_checked.v1`, `ops.policy_violation.v1`, persisted `risk_state` and `risk_decision_log`).
- `DEV-0020` completed: deterministic `execution-gateway` baseline implemented in Rust with persisted `execution_order_journal` and project-wide `audit_event_log` contract.
- `DEV-0021` completed: broker-venue adapter baseline added to `execution-gateway` for live submit/amend/cancel and broker ack/fill ingest (`exec.order_command.v1`, `broker.execution.ack.v1`) with `execution_command_log` persistence.
- `DEV-0023` completed: deterministic `portfolio-engine` baseline added with persisted position/account/fill state and `portfolio.snapshot.v1` emission; `risk-engine` upgraded with portfolio-aware exposure/equity constraints.
- Control-panel program ticket set opened (`DEV-0024..DEV-0034`) for phased enterprise admin console delivery with shadcn black-and-white UI direction and charting sub-module integration.

## Current

- Section 5.1 hard-gate enforcement active with deterministic-core migration batch completed.
- `DEV-00013` is closed with live runtime evidence and explicit surfaced external-network adapter error diagnostics.
- `DEV-00014` is closed with live runtime adapter-check and coverage evidence.
- `DEV-0018` is closed with deterministic runtime baseline, compose wiring, topic contracts, and test pack (`dev-0018`).
- `DEV-0019` is closed with deterministic runtime baseline, compose wiring, topic/schema contracts, and test pack (`dev-0019`).
- `DEV-0020` is closed with deterministic runtime baseline, execution topics, and audit/journal persistence contract in runtime + schema.
- `DEV-0021` is closed with broker adapter baseline, command/ack topics, and extended execution journal/command persistence contract.
- `DEV-0022` is now open and in progress for execution adapter network resilience (DNS/connectivity/runtime robustness).
- `DEV-0023` is closed with deterministic portfolio-state baseline and richer risk constraints.

## Next

1. Deliver `DEV-0022` implementation for timeout/name-resolution handling and bounded retry/backoff tuning.
2. Start `DEV-0025` control panel foundation shell and black-and-white design-system implementation.
3. Sequence `DEV-0026..DEV-0030` for RBAC and core operations modules (ingestion, risk/portfolio, execution OMS, charting workbench).

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
