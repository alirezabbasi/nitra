# Current State Snapshot

Last updated: 2026-04-29

## Where Are We Snapshot

### Completed

- Ingestion baseline delivery completed for `DEV-00001..DEV-00007`.
- Development operating system and persistent memory framework established under `docs/development/`.
- HLD Section 5 coverage assessment completed and mapped to roadmap statuses.
- Documentation system unified with canonical entrypoints and de-duplicated delivery artifacts.

### Recent

- Reviewed control-panel implementation and confirmed production-structure gap:
  - `services/charting/app.py` remains a large monolith with mixed concerns.
  - `services/charting/static/control-panel.html` remains single-file UI architecture.
- Opened control-panel refactor program set `DEV-00044..DEV-00051` for monolith-to-modular migration.
- Added dedicated target LLD document for renamed `control-panel-service` structure:
  - `docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md`.
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
- Completed `DEV-00018` deterministic structure-engine baseline:
  - replaced `structure-engine` scaffold with runnable Rust runtime,
  - consumes `bar.1m`, emits `structure.snapshot.v1`/`structure.pullback.v1`/`structure.minor_confirmed.v1`/`structure.major_confirmed.v1`,
  - persists single-source-of-truth state in `structure_state`,
  - added compose/topic/schema contracts plus `tests/dev-0018`.
- Completed `DEV-00019` deterministic risk-engine baseline:
  - replaced `risk-engine` scaffold with runnable Rust runtime,
  - consumes configurable input stream (baseline `structure.snapshot.v1`) and enforces deterministic policy checks,
  - emits `decision.risk_checked.v1` and `ops.policy_violation.v1`,
  - persists `risk_state` and `risk_decision_log` with idempotent processing semantics.
- Completed `DEV-00020` deterministic execution-gateway baseline + audit/journal persistence contract:
  - replaced `execution-gateway` scaffold with runnable Rust runtime,
  - consumes `decision.risk_checked.v1` and emits `exec.order_submitted.v1` / `exec.order_updated.v1` / `exec.fill_received.v1` / `exec.reconciliation_issue.v1`,
  - persists lifecycle state to `execution_order_journal`,
  - persists cross-service trace events to `audit_event_log`,
  - preserves idempotent processing semantics via `processed_message_ledger`.
- Completed `DEV-00021` broker-venue adapter baseline for execution-gateway:
  - added live broker submit/amend/cancel adapter routes with deterministic dry-run fallback,
  - added ack/fill ingest stream consumption (`broker.execution.ack.v1`) and order-command stream (`exec.order_command.v1`),
  - persisted command decisions to `execution_command_log`,
  - extended execution journal with `broker_order_id` and `state_version`.
- Completed `DEV-00023` deterministic portfolio baseline + richer risk constraints:
  - added runnable Rust `portfolio-engine` with fill-driven state updates and `portfolio.snapshot.v1` emission,
  - added portfolio persistence contracts: `portfolio_position_state`, `portfolio_account_state`, `portfolio_fill_log`,
  - wired risk-engine portfolio-aware limits (`max_symbol_exposure`, `max_portfolio_gross_exposure`, `min_available_equity`).
- Opened control-panel program planning set (`DEV-00024..DEV-00034`) with phased enterprise admin panel delivery:
  - shadcn-based black-and-white design system direction,
  - sidebar-first multi-module information architecture,
  - charting integration as control-panel sub-module (`Full Chart` from instrument profile).
- Completed `DEV-00025` control panel foundation shell baseline:
  - added FastAPI route `/control-panel` and overview API `/api/v1/control-panel/overview`,
  - added professional black-and-white sidebar admin shell (`services/charting/static/control-panel.html`),
  - integrated module health and core operational metric cards for first-pass operator overview.
- Completed `DEV-00026` control panel authentication/RBAC baseline:
  - added token-authenticated control-panel session contract with roles (`viewer`, `operator`, `risk_manager`, `admin`),
  - enforced route guards for control-panel endpoints and role-based sidebar visibility hooks,
  - added privileged-action endpoint with justification requirement and `control_panel_audit_log` persistence.
- Completed `DEV-00027` control panel market ingestion/data-quality operations baseline:
  - added ingestion operations API `/api/v1/control-panel/ingestion` (connector matrix, coverage/gap, backfill and replay status views),
  - added guarded recovery action `/api/v1/control-panel/ingestion/backfill-window` (operator+ role, justification required, 7-day safety cap),
  - added dedicated ingestion workspace in control-panel UI with live tables and safe-recovery workflow.
- Completed `DEV-00028` control panel strategy/risk/portfolio center baseline:
  - added `/api/v1/control-panel/risk-portfolio` for strategy health rollups, symbol exposure snapshots, violation forensics, and portfolio headroom,
  - added `/api/v1/control-panel/risk-limits` with bounded validation and `risk_manager+` role gate,
  - added `/api/v1/control-panel/risk/kill-switch` for global/market kill-switch control with audited mutation flow,
  - added risk/portfolio workspace UI section with limits editor, kill-switch controls, and live posture tables.
- Completed `DEV-00029` control panel execution OMS/broker-ops baseline:
  - added `/api/v1/control-panel/execution` for order lifecycle, command log, reconciliation queue, and broker diagnostics views,
  - added `/api/v1/control-panel/execution/command` for role-gated amend/cancel workflows with justification and audit trails,
  - added execution workspace UI section with order blotter, command form, reconciliation table, and broker diagnostics.
- Completed `DEV-00030` control panel charting workbench integration baseline:
  - added `/api/v1/control-panel/charting/profile` for instrument profile + operational context (latest bar, risk, execution, gap state),
  - added dedicated charting workspace with split-view profile panel + embedded live chart frame,
  - added one-click context handoff from ingestion/risk/execution tables into chart workbench (`openChartWorkbench`).
- Completed `DEV-00031` control panel alerting/incidents/runbooks center baseline:
  - added `/api/v1/control-panel/ops` for alert inbox, incident workspace, and runbook execution telemetry,
  - added `/api/v1/control-panel/ops/alerts/ingest` + `/api/v1/control-panel/ops/alerts/action` for lifecycle ownership/suppression/incident creation flows,
  - added `/api/v1/control-panel/ops/runbook/execute` with auditable runbook execution persistence,
  - added ops workspace UI section with alert queue, incident table, and runbook launcher/history.
- Completed `DEV-00032` control panel research/backtesting/model-ops center baseline:
  - added `/api/v1/control-panel/research` for dataset registry, backtest history, and model registry visibility,
  - added `/api/v1/control-panel/research/backtest` for role-gated backtest launch workflow,
  - added `/api/v1/control-panel/research/model/promote` for readiness/stage gate updates with audit trail,
  - added research workspace UI section with dataset lineage table, backtest launcher/history, and model promotion gate controls.
- Completed `DEV-00033` control panel config/change-control/governance center baseline:
  - added `/api/v1/control-panel/config` for typed environment-aware registry and governance metrics,
  - added `/api/v1/control-panel/config/propose`, `/approve`, `/apply`, `/rollback` with RBAC and justification policy,
  - added immutable change history and request-tracking contracts (`control_panel_config_change_request`, `control_panel_config_change_history`),
  - added config workspace UI section with proposal, approval, apply, rollback, and history views.
- Completed `DEV-00034` control panel enterprise polish/performance/accessibility baseline:
  - added global command palette (`Ctrl/Cmd+K`) backed by `/api/v1/control-panel/search`,
  - added persisted operator preferences (last section + compact/comfortable density),
  - added keyboard/focus accessibility hardening (`skip-link`, `focus-visible`, modal semantics),
  - added bounded render slice helper to reduce heavy-table paint cost.
- Completed `DEV-00022` execution adapter network resilience hardening:
  - implemented deterministic bounded retry/backoff policy for submit/amend/cancel broker calls,
  - added explicit failure classification (`dns_resolution`, timeout/connect, `upstream_5xx`, etc.) in journal/audit metadata,
  - emitted reconciliation issues with network-failure context for terminal adapter failures,
  - added degraded-mode cooldown safeguard to reduce uncontrolled retry bursts.
- Completed `DEV-00024` control-panel program epic closure:
  - consolidated delivery evidence map across `DEV-00025..DEV-00034`,
  - confirmed enterprise control-panel program scope is fully delivered and documented.
- Registered second-chain strengthening delivery set `DEV-00035..DEV-00043`:
  - strict execution sequence for `structure -> feature -> signal -> risk -> execution -> portfolio -> journal`,
  - contract-first and replay-determinism gates before deeper runtime expansion.
- Completed `DEV-00035` second-chain hardening program epic:
  - verified ordered implementation-ready ticket sequence `DEV-00036..DEV-00043`,
  - confirmed deterministic guardrails and verification criteria at each chain stage,
  - synchronized Kanban/active-focus/memory artifacts for execution handoff.

### Current

- `DEV-00013` closed with live runtime evidence and explicit surfaced error-state diagnostics.
- `DEV-00014` closed with live adapter-check and coverage evidence.
- `DEV-00018` closed with deterministic structure runtime baseline in production compose path.
- `DEV-00019` closed with deterministic risk runtime baseline in production compose path.
- `DEV-00020` closed with deterministic execution runtime baseline and persisted audit/journal contract.
- `DEV-00021` closed with broker adapter baseline and ack/fill ingest path.
- `DEV-00022` closed with deterministic network-resilience behavior and triage-ready failure context.
- `DEV-00023` closed with deterministic portfolio-state baseline and richer portfolio-aware risk controls.
- `DEV-00027` closed with ingestion/data-quality operations center baseline in control panel.
- `DEV-00028` closed with strategy/risk/portfolio control center baseline in control panel.
- `DEV-00029` closed with execution OMS and broker-operations center baseline in control panel.
- `DEV-00030` closed with charting workbench integration baseline in control panel.
- `DEV-00031` closed with alerting/incidents/runbooks center baseline in control panel.
- `DEV-00032` closed with research/backtesting/model-ops center baseline in control panel.
- `DEV-00033` closed with config/change-control/governance center baseline in control panel.
- `DEV-00034` closed with enterprise polish/performance/accessibility baseline in control panel.
- `DEV-00024` closed with consolidated child-ticket delivery evidence.
- `DEV-00035` is closed with deterministic hardening sequence and acceptance gates fully defined.
- Section 5.1 enforcement active (policy-as-code + hard gates) with migration batch completed.

### Next

1. Execute `DEV-00036` cross-chain contracts, schema gates, and replay determinism.
2. Execute `DEV-00037` structure-engine production deterministic hardening.
3. Execute `DEV-00038` feature-service deterministic baseline with point-in-time integrity.

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
- Partial: normalization/replay path, structure-engine baseline, risk-engine baseline, execution-gateway baseline, audit/journal contract baseline, raw data lake archival, MLflow/research infra, observability basics.
- Scaffold only: llm-analyst.
- Not started: feature platform (Feast), full online inference layer (Ray Serve).

## Section 5.1 Compliance Snapshot

- Enforcement mode: hard-gate now (`make enforce-section-5-1`).
- Gate runner: local scripts + Make targets (CI-ready).
- Deterministic-core non-compliant migrating services:
  - none
- Blocked rule active: no net-new deterministic Python feature scope.
