# Where Are We

Last updated: 2026-04-29

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
- `DEV-00018` completed: deterministic `structure-engine` baseline implemented in Rust (`bar.1m` consumer, structure topics, persisted `structure_state`, idempotent ledger semantics).
- `DEV-00019` completed: deterministic `risk-engine` baseline implemented in Rust (policy checks, `decision.risk_checked.v1`, `ops.policy_violation.v1`, persisted `risk_state` and `risk_decision_log`).
- `DEV-00020` completed: deterministic `execution-gateway` baseline implemented in Rust with persisted `execution_order_journal` and project-wide `audit_event_log` contract.
- `DEV-00021` completed: broker-venue adapter baseline added to `execution-gateway` for live submit/amend/cancel and broker ack/fill ingest (`exec.order_command.v1`, `broker.execution.ack.v1`) with `execution_command_log` persistence.
- `DEV-00023` completed: deterministic `portfolio-engine` baseline added with persisted position/account/fill state and `portfolio.snapshot.v1` emission; `risk-engine` upgraded with portfolio-aware exposure/equity constraints.
- Control-panel program ticket set opened (`DEV-00024..DEV-00034`) for phased enterprise admin console delivery with shadcn black-and-white UI direction and charting sub-module integration.
- `DEV-00025` completed: control-panel foundation shell baseline implemented in FastAPI charting service with professional black-and-white sidebar layout and overview metrics endpoint.
- `DEV-00026` completed: control-panel auth/RBAC baseline implemented with token-backed operator sessions, role-aware route guards, and privileged-action audit trail.
- `DEV-00027` completed: control-panel ingestion/data-quality operations baseline implemented with connector/coverage/replay visibility and guarded backfill-window recovery action.
- `DEV-00028` completed: control-panel strategy/risk/portfolio center baseline implemented with live posture views, risk-limit editor, and kill-switch controls under RBAC + audit flow.
- `DEV-00029` completed: control-panel execution OMS/broker-ops center baseline implemented with order lifecycle visibility, command workflows, reconciliation queue, and broker diagnostics.

## Current

- Section 5.1 hard-gate enforcement active with deterministic-core migration batch completed.
- `DEV-00013` is closed with live runtime evidence and explicit surfaced external-network adapter error diagnostics.
- `DEV-00014` is closed with live runtime adapter-check and coverage evidence.
- `DEV-00018` is closed with deterministic runtime baseline, compose wiring, topic contracts, and test pack (`dev-0018`).
- `DEV-00019` is closed with deterministic runtime baseline, compose wiring, topic/schema contracts, and test pack (`dev-0019`).
- `DEV-00020` is closed with deterministic runtime baseline, execution topics, and audit/journal persistence contract in runtime + schema.
- `DEV-00021` is closed with broker adapter baseline, command/ack topics, and extended execution journal/command persistence contract.
- `DEV-00022` is now open and in progress for execution adapter network resilience (DNS/connectivity/runtime robustness).
- `DEV-00023` is closed with deterministic portfolio-state baseline and richer risk constraints.
- `DEV-00027` is closed with ingestion/data-quality operations center baseline in control panel.
- `DEV-00028` is closed with strategy/risk/portfolio control center baseline in control panel.
- `DEV-00029` is closed with execution OMS and broker operations center baseline in control panel.

## Next

1. Deliver `DEV-00022` implementation for timeout/name-resolution handling and bounded retry/backoff tuning.
2. Sequence `DEV-00030` for charting workbench integration module.
3. Continue `DEV-00031..DEV-00034` governance, enterprise polish, and release-hardening modules.

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
