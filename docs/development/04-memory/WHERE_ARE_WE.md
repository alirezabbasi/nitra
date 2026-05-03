# Where Are We

Last updated: 2026-05-03

## Completed

- `DEV-00001..DEV-00007` ingestion baseline is complete.
- Development operating system and memory system are in place.
- Project-wide documentation system has been unified and cross-links cleaned.

## Recent

- Completed `DEV-00078` normalization/replay sequence/order integrity verifier with persisted source-sequence plus normalized-order verdicts.
- Completed `DEV-00072` replay manifest/index service with deterministic selection ordering, checksum provenance, and control-panel build workflow.
- Completed `DEV-00071` raw data lake canonical partition/object-key strategy with manifest-level replay provenance and control-panel ops visibility.
- Completed `DEV-00143` raw message capture conformance with untouched payload persistence and sequence provenance checks plus control-panel ops visibility.
- Completed paired P0 feed-operations slice:
  - `DEV-00070` feed-quality SLA metrics contract (latency/drop/sequence/heartbeat) in connector health + control-panel ingestion API/UI.
  - `DEV-00142` rate-limit governance + adaptive throttling contract with per-venue policy controls.
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
- `DEV-00030` completed: control-panel charting workbench integration baseline implemented with instrument profile API, split-view chart workspace, and one-click context handoff from ops modules.
- `DEV-00031` completed: control-panel alerting/incidents/runbooks baseline implemented with alert lifecycle actions, incident workspace, and audited runbook execution contract.
- `DEV-00032` completed: control-panel research/backtesting/model-ops baseline implemented with dataset lineage registry, backtest launcher/history, and model promotion gate controls.
- `DEV-00033` completed: control-panel config/governance baseline implemented with typed registry, controlled proposal/approve/apply/rollback flows, and immutable change history.
- `DEV-00034` completed: control-panel enterprise polish baseline implemented with command palette search, persisted operator layout/density preferences, keyboard/focus accessibility hardening, and bounded render slices.
- `DEV-00022` completed: execution adapter network resilience hardening implemented with deterministic bounded retry/backoff, failure classification, degraded-mode cooldown guard, and reconciliation-context emission.
- `DEV-00024` completed: control-panel program epic closed with consolidated evidence across `DEV-00025..DEV-00034`.
- Registered second-chain strengthening ticket set `DEV-00035..DEV-00043` to prioritize hardening of `structure -> feature -> signal -> risk -> execution -> portfolio -> journal`.
- `DEV-00035` completed: second-chain hardening program finalized with ordered implementation tickets `DEV-00036..DEV-00043` and deterministic acceptance gates.
- `DEV-00036` completed: canonical second-chain schema contracts and replay-determinism verification gates delivered (`dev-0036`).
- `DEV-00037` completed: structure-engine deterministic hardening delivered with illegal-transition guards, out-of-order replay protection, and persisted transition-reason state.
- `DEV-00038` completed: feature-service deterministic baseline delivered with PIT-safe transforms, lineage persistence contract, and reproducibility checks.
- `DEV-00039` completed: deterministic signal scorer baseline delivered with explainability reason codes, calibration harness, and pinned scorer/model versions.
- `DEV-00040` completed: risk policy coverage expanded with canonical policy IDs, persisted evaluation traces, and stress-tested fail-closed interaction behavior.
- `DEV-00041` completed: execution lifecycle hardening delivered with valid-transition guards, stale/duplicate command rejection, and reconciliation SLA context emission.
- `DEV-00042` completed: portfolio authoritative reconciliation baseline delivered with invariant checks, drift taxonomy, and persisted reconciliation evidence.
- `DEV-00043` completed: taxonomy-versioned execution audit payloads and incident evidence bundle export contract delivered with regression checks.
- Converted the remaining roadmap backlog item into concrete ticket `DEV-00064` with acceptance criteria and `dev-0064` verification pack.
- Decomposed all remaining HLD Section 5 architecture scope into atomic component tickets `DEV-00065..DEV-00122` and queued them in Kanban backlog.
- Added mandatory control-panel companion stream `DEV-00123..DEV-00140` to ensure each remaining component has explicit operator UI section(s) and configuration management workflows.
- Added global rule requiring control-panel integration for every new feature and published dedicated control-panel product/UI architecture doc in `docs/design/`.
- Reordered remaining roadmap into deterministic-first priorities (P0->P8): data/replay/risk/execution first; ML/LLM layers explicitly later.

## Current

- `DEV-00078` closed (`test-dev-0078`).
- `DEV-00077` closed (`test-dev-0077`).
- `DEV-00126` closed (`test-dev-0126`).
- `DEV-00125` closed (`test-dev-0125`).
- `DEV-00076` closed (`test-dev-0076`).
- `DEV-00075` closed (`test-dev-0075`).
- `DEV-00074` closed (`test-dev-0074`).
- `DEV-00073` closed (`test-dev-0073`).
- `DEV-00072` closed (`test-dev-0072`).
- `DEV-00071` closed (`test-dev-0071`).
- `DEV-00143` closed (`test-dev-0143`).
- `DEV-00070` closed (`test-dev-0070`).
- `DEV-00142` closed (`test-dev-0142`).
- Section 5.1 hard-gate enforcement active with deterministic-core migration batch completed.
- `DEV-00013` is closed with live runtime evidence and explicit surfaced external-network adapter error diagnostics.
- `DEV-00014` is closed with live runtime adapter-check and coverage evidence.
- `DEV-00018` is closed with deterministic runtime baseline, compose wiring, topic contracts, and test pack (`dev-0018`).
- `DEV-00019` is closed with deterministic runtime baseline, compose wiring, topic/schema contracts, and test pack (`dev-0019`).
- `DEV-00020` is closed with deterministic runtime baseline, execution topics, and audit/journal persistence contract in runtime + schema.
- `DEV-00021` is closed with broker adapter baseline, command/ack topics, and extended execution journal/command persistence contract.
- `DEV-00022` is closed with deterministic network-resilience policy and operator triage context in runtime/audit events.
- `DEV-00023` is closed with deterministic portfolio-state baseline and richer risk constraints.
- `DEV-00027` is closed with ingestion/data-quality operations center baseline in control panel.
- `DEV-00028` is closed with strategy/risk/portfolio control center baseline in control panel.
- `DEV-00029` is closed with execution OMS and broker operations center baseline in control panel.
- `DEV-00030` is closed with charting workbench integration baseline in control panel.
- `DEV-00031` is closed with alerting, incidents, and runbooks center baseline in control panel.
- `DEV-00032` is closed with research/backtesting/model-ops center baseline in control panel.
- `DEV-00033` is closed with config registry/change-control/governance center baseline in control panel.
- `DEV-00034` is closed with enterprise polish/performance/accessibility baseline in control panel.
- `DEV-00024` is closed with full child-ticket delivery evidence map.
- `DEV-00035` is closed with second-chain hardening sequence and verification gates defined.
- `DEV-00036` is closed with contract/schema baselines and deterministic replay equivalence tests.
- `DEV-00037` is closed with production deterministic transition guards and replay ordering safety.
- `DEV-00038` is closed with deterministic feature baseline and no-lookahead lineage contract.
- `DEV-00039` is closed with deterministic scored-signal contract and explainability payload baseline.
- `DEV-00040` is closed with deterministic policy-trace metadata in risk events and persistence.
- `DEV-00041` is closed with execution lifecycle guardrails and reconciliation SLA observability context.
- `DEV-00042` is closed with authoritative portfolio reconciliation checks and drift alert emission.
- `DEV-00043` is closed with end-to-end journal evidence fabric and incident bundle export baseline.
- `DEV-00044` is closed after completion of `DEV-00045..DEV-00051`; status is normalized across Kanban and memory artifacts.
- `DEV-00057` is closed with control-panel program reconciliation completed in the same session.
- `DEV-00063` is closed with sustained-load observability evidence captured and route parity fix applied for `/api/v1/charting/markets/available`.
- `DEV-00045` is closed with target architecture freeze and migration compatibility contract artifacts.
- `DEV-00046` is closed with backend foundation skeleton and `control-panel` compose service cutover.
- `DEV-00047` is closed with control-panel domain router split and service-layer proxy extraction.
- `DEV-00048` is closed with control-panel charting module extraction and compatibility/deprecation bridge.
- `DEV-00049` is closed with control-panel frontend app-shell modularization and source/dist pipeline hardening.
- `DEV-00050` is closed with control-panel backend/frontend/compatibility aggregate quality gates and CI-ready enforcement command.
- `DEV-00051` is closed with control-panel native charting cutover, legacy alias retirement, and published rollout/deprecation closure artifacts.
- `DEV-00052` is closed with live-adapter reconciliation/runbook evidence capture expansion and verification gate coverage.
- `DEV-00064` remains a completed roadmap-conversion artifact.
- `DEV-00065..DEV-00122` now define the execution path required to reach full Section 5 architecture completion.
- `DEV-00123..DEV-00140` define required control-panel module/config governance evolution running in lockstep with component delivery.
- Backlog now follows strict build order: P0 ingestion/raw/kafka, P1 normalization/replay/storage/structure, then research, decisioning, control, execution, observability, and finally LLM/RAG.
- `DEV-00065` is now closed with governance deliverables completed (`DETERMINISTIC_EXECUTION_DEPENDENCY_MAP.md`, `SECTION5_CLOSURE_CRITERIA.md`, `test-dev-0065`).
- `DEV-00068` and `DEV-00124` are now closed with paired failover-policy backend + control-panel operator controls delivered (`dev-0068`).
- `DEV-00069` and `DEV-00141` are now closed with paired session lifecycle + websocket/session reliability controls delivered (`dev-0069`).

## Next

1. Continue with `DEV-00079` normalization/replay 90-day startup-coverage conformance harness scope.

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
