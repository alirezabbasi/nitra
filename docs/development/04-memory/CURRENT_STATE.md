# Current State Snapshot

Last updated: 2026-05-01

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
- Completed `DEV-00036` second-chain contracts and replay determinism:
  - published canonical second-chain contract baseline and schema artifacts (`contracts/second-chain/*.schema.json`),
  - added deterministic replay equivalence unit tests in `structure-engine` and `risk-engine`,
  - added executable contract/determinism verification pack (`tests/dev-0036/run.sh`, `make test-dev-0036`).
- Completed `DEV-00037` structure-engine production deterministic hardening:
  - added transition invariant validator to block illegal state-machine paths,
  - added explicit out-of-order/duplicate replay bar protection (`bucket_start` monotonic guard),
  - persisted transition reason codes in `structure_state.last_transition_reason` with migration `012_structure_transition_reason.sql`,
  - added executable hardening verification pack (`tests/dev-0037/run.sh`, `make test-dev-0037`).
- Completed `DEV-00038` feature-service deterministic baseline and PIT integrity:
  - added Python `feature-service` baseline runtime with deterministic feature transforms from structure snapshots,
  - enforced no-lookahead baseline contract via previous-state-only feature computation path,
  - added persisted feature lineage contract in `feature_snapshot` with migration `013_feature_snapshot.sql`,
  - wired compose/topics/policy for `features.snapshot.v1` flow and service activation,
  - added executable verification pack (`tests/dev-0038/run.sh`, `make test-dev-0038`).
- Completed `DEV-00039` signal-engine deterministic scorer and explainability baseline:
  - added deterministic scored-signal runtime path in `services/inference-gateway/app.py`,
  - added explainability payload contract (`reason_codes`, `feature_refs`) with pinned scorer/model/feature versions,
  - added calibration harness (`run_calibration`) for reproducible score distribution validation,
  - switched risk baseline input topic to `decision.signal_scored.v1`,
  - added persistence migration `014_signal_score_log.sql` and test pack (`tests/dev-0039/run.sh`, `make test-dev-0039`).
- Completed `DEV-00040` risk policy expansion and decision traceability hardening:
  - expanded deterministic risk policy checks (volatility, conflict, strict kill-switch variant),
  - added canonical risk policy IDs (`RISK-*`) and policy-hit trace emission on all decisions,
  - added persisted evaluation traces (`policy_hits`, `evaluation_trace`) for forensic diagnostics,
  - added schema migration `015_risk_policy_trace.sql`,
  - added stress/regression verification pack (`tests/dev-0040/run.sh`, `make test-dev-0040`).
- Completed `DEV-00041` execution lifecycle controls and reconciliation SLA hardening:
  - added strict lifecycle transition guardrails for command/ack status changes,
  - added deterministic stale/duplicate command rejection controls,
  - added reconciliation SLA breach context fields (`sla_seconds`, `age_seconds`) in issue events,
  - added execution verification pack (`tests/dev-0041/run.sh`, `make test-dev-0041`).
- Completed `DEV-00042` portfolio authoritative reconciliation and state invariants:
  - added deterministic reconciliation checks between computed position aggregates and account-state aggregates,
  - added invariant breach taxonomy (gross/net exposure mismatch, limit breaches, min-equity breach),
  - added persisted reconciliation evidence contract `portfolio_reconciliation_log` via migration `016_portfolio_reconciliation_log.sql`,
  - added drift issue emission contract (`portfolio_reconciliation_drift`) for actionable operator triage,
  - added verification pack (`tests/dev-0042/run.sh`, `make test-dev-0042`).
- Completed `DEV-00043` journal evidence fabric and incident bundle export:
  - added incident evidence bundle persistence contract `incident_evidence_bundle` via migration `017_incident_evidence_bundle.sql`,
  - added audit taxonomy versioning control via `EXEC_AUDIT_TAXONOMY_VERSION`,
  - added lineage/correlation propagation and bundle auto-export hooks on rejected/terminal execution outcomes,
  - added verification pack (`tests/dev-0043/run.sh`, `make test-dev-0043`).
- Completed `DEV-00048` control-panel charting module extraction and compatibility bridge:
  - added dedicated charting router and charting proxy module under `services/control-panel`,
  - preserved legacy charting endpoints with explicit deprecation/sunset successor headers,
  - added `dev-0048` verification pack and make target.
- Completed `DEV-00049` control-panel frontend app-shell restructure and UI architecture hardening:
  - extracted monolithic control-panel HTML inline CSS/JS into modular frontend source structure under `services/control-panel/frontend/src`,
  - added reproducible `src -> dist` build/sync script and runtime `frontend/dist` artifact contract,
  - updated control-panel service to serve `/control-panel` and `/control-panel-assets` from native frontend dist path.
- Completed `DEV-00050` control-panel refactor quality gates and CI readiness:
  - added aggregate quality gate suite (`dev-0050`) covering backend/frontend/compatibility checks,
  - added CI-ready command wrapper for deterministic merge gating,
  - published DevOps-quality-gates documentation for reproducible enforcement.
- Completed `DEV-00051` control-panel refactor rollout, cutover, and deprecation closure:
  - retired legacy charting alias endpoints and finalized native `/api/v1/charting/*` canonical route family,
  - added migration status observability endpoint and native cutover status signaling,
  - published rollout/rollback runbook and deprecation closure report with verification evidence.

### Current

- `DEV-00068` is closed with failover policy contract delivery (policy table + update endpoint + audit integration + `dev-0068` gate).
- `DEV-00124` is closed with control-panel feeds failover controls (runtime metrics, policy table, guarded policy-update form).
- `DEV-00069` is closed with credential/session lifecycle hardening (session policy contract + guarded mutation endpoint + runtime visibility + `dev-0069` gate).
- `DEV-00141` is closed with websocket/session manager hardening (heartbeat/stale/reconnect policy contract + control-panel ops controls + `dev-0069` gate).
- `DEV-00065` is closed with governance deliverables published: deterministic dependency map + Section 5 closure criteria contract + executable verification target (`test-dev-0065`).
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
- `DEV-00036` is closed with canonical contract baseline and replay determinism checks.
- `DEV-00037` is closed with deterministic transition guards and replay ordering protection.
- `DEV-00038` is closed with deterministic PIT-safe feature baseline and lineage persistence.
- `DEV-00039` is closed with deterministic scored-signal baseline and explainability contract.
- `DEV-00040` is closed with deterministic policy-trace metadata and stress-tested fail-closed interactions.
- `DEV-00041` is closed with lifecycle transition safety and reconciliation SLA triage context.
- `DEV-00042` is closed with authoritative reconciliation invariants and drift evidence emission.
- `DEV-00043` is closed with taxonomy-versioned audit payloads and incident bundle export contract.
- `DEV-00044` is closed after completion of `DEV-00045..DEV-00051`; closure state is normalized across Kanban and memory artifacts.
- `DEV-00057` is closed with reconciliation completed for ticket/Kanban/memory status consistency.
- `DEV-00045` is closed with architecture/migration contract freeze artifacts (`control-panel-service` LLD expansion + migration map + compatibility matrix).
- `DEV-00046` is closed with backend modularization foundation (`services/control-panel`) and compose service-boundary rename.
- `DEV-00047` is closed with domain router split and service-layer proxy extraction for control-panel APIs.
- `DEV-00048` is closed with charting module extraction and compatibility/deprecation bridge coverage.
- `DEV-00049` is closed with frontend source/dist app-shell architecture hardening and native asset serving path.
- `DEV-00050` is closed with aggregate quality gate coverage and CI-readiness command path.
- `DEV-00051` is closed with native charting cutover, shim retirement, and rollout/deprecation closure artifacts.
- `DEV-00052` is closed with live-adapter reconciliation/runbook evidence capture expansion (`control_panel_reconciliation_evidence`, runbook evidence_summary payloads, `dev-0052` gate).
- `DEV-00053` is closed with control-panel ingestion KPI monitoring for per-market 130k `1m` OHLCV target progress and raw-tick realtime lag SLA (`/api/v1/control-panel/ingestion/kpi`, `dev-0053` gate).
- `DEV-00054` is closed with chart-level liquidity-structure overlay toggle (`Liquidity Layer`) implementing pullback/minor/major visual interpretation directly on instrument charts (`dev-0054` gate).
- `DEV-00055` is closed with architecture-level interpretation governance formalization: HLD integration plus dedicated LLD defining seven mandatory artifacts (ontology, rulebook, scenarios, output schema, RAG taxonomy, benchmark, prompt contract).
- `DEV-00056` is closed with canonical liquidity ontology baseline documentation and explicit chart-layer legend semantics for project-wide analytical consistency (`dev-0055` gate).
- Section 5.1 enforcement active (policy-as-code + hard gates) with migration batch completed.
- `DEV-00063` is closed with sustained-load observability evidence captured and route parity fix applied for `/api/v1/charting/markets/available`.
- Roadmap conversion backlog item is closed by registering `DEV-00064` with explicit acceptance criteria and verification target (`test-dev-0064`).
- Section 5 remaining architecture scope is decomposed into atomic component tickets `DEV-00065..DEV-00122` and added to backlog as the completion path to `100%`.
- Added mandatory control-panel companion ticket stream `DEV-00123..DEV-00140` so each remaining Section 5 component ships with explicit UI section coverage and configuration management controls.
- Elevated control-panel governance to global policy (`docs/ruleset.md` Rule 16) and added dedicated product/UI architecture document (`docs/design/control-panel-product-and-ui.md`).
- Rebased remaining Section 5 backlog to deterministic-first build order (P0->P8), explicitly deferring Feast/Ray/MLflow maturity and LLM/RAG to later priorities.

### Next

1. Execute Priority 0 (ingestion + raw lake + Kafka) with deterministic evidence and paired control-panel modules.
2. Execute Priority 1 (normalization/replay + timeseries + structure) before any higher-priority ML/LLM work.

### Risks/Blocks

- Risk of architecture drift toward ingestion-only progress.
- Risk of context drift if memory files are not updated at session close.
- Open decision: priority ordering between replay controller and structure-engine first slice.
- Open dependency: adapter correctness is implemented and observable, but success rate depends on stable outbound network/DNS in runtime.
- External risk: Coinbase Exchange candles endpoint may return 403 in some runtimes; fallback route health must be monitored.
- Runtime restart needed to clear historical mock-origin rows from operational validation windows.

## Program status

- Overall project phase: transition from ingestion baseline to core deterministic engine implementation.
- Active focus: deterministic-first execution (P0->P8) with mandatory control-panel parity for each component.

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
