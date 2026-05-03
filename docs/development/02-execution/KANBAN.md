# NITRA Project Kanban

Last updated: 2026-05-03

## Backlog

### Priority 0 — Non-Negotiable Core (Data Acquisition)

- [ ] (No pending P0 items)

### Priority 1 — Deterministic Market Data Foundation

- [ ] `DEV-00079` Normalization/Replay - full 90-day startup-coverage conformance harness with venue-session edge-case fixtures.
- [ ] `DEV-00144` Normalization/Replay - canonical validation suite (tick/trade/order-book validators and deterministic reject taxonomy).
- [ ] `DEV-00145` Normalization/Replay - deterministic deduplication conformance pack across ingestion/normalization/replay boundaries.
- [ ] `DEV-00083` Time-Series Storage - continuous aggregate/materialization strategy for operational and research query workloads.
- [ ] `DEV-00084` Time-Series Storage - compression/retention policy rollout with deterministic restore verification.
- [ ] `DEV-00085` Time-Series Storage - schema/index performance hardening under sustained replay and live ingest concurrency.
- [ ] `DEV-00080` Deterministic Structure Engine - rulebook-complete implementation audit (inside/outside/pullback/minor/major edge paths).
- [ ] `DEV-00081` Deterministic Structure Engine - state snapshot versioning and deterministic migration harness for long-horizon replay stability.
- [ ] `DEV-00082` Deterministic Structure Engine - structure regression benchmark pack (historical fixture library + invariants report).
- [ ] `DEV-00146` Deterministic Structure Engine - liquidity-zone/swing-state deterministic replay conformance across fractal timeframes.
- [ ] `DEV-00127` Control Panel (P1) - normalization/replay module (quarantine triage, integrity reports, coverage console).
- [ ] `DEV-00129` Control Panel (P1) - time-series storage module (aggregates/compression/query diagnostics/retention controls).
- [ ] `DEV-00128` Control Panel (P1) - structure module (rule-state inspector, snapshot versions, benchmark evidence).

### Priority 2 — Research and Validation

- [ ] `DEV-00091` Research/Backtesting - deterministic dataset builder pipeline with reproducible snapshot manifests.
- [ ] `DEV-00092` Research/Backtesting - walk-forward validator framework and baseline evaluation scenarios.
- [ ] `DEV-00093` Research/Backtesting - labeling framework contracts and quality validation for supervised pipelines.
- [ ] `DEV-00094` Research/Backtesting - experiment runner orchestration with standardized metric and artifact capture.
- [ ] `DEV-00147` Research/Backtesting - strategy simulation realism pack (slippage, fee, latency, and regime-tag fidelity checks).
- [ ] `DEV-00131` Control Panel (P2) - research module expansion (dataset/backtest/walk-forward/labeling governance controls).

### Priority 3 — Decision Layer

- [ ] `DEV-00086` Feature Platform - bootstrap feature repository and registry contracts aligned to existing feature-service outputs.
- [ ] `DEV-00087` Feature Platform - online store integration and retrieval APIs for low-latency inference consumption.
- [ ] `DEV-00088` Feature Platform - offline store and point-in-time dataset materialization pipeline.
- [ ] `DEV-00089` Feature Platform - training-serving skew detection gates and parity assertions in CI.
- [ ] `DEV-00090` Feature Platform - feature versioning/deprecation policy with backfill-safe migration workflow.
- [ ] `DEV-00096` Online Inference - baseline serving deployment integrating signal/regime/aggregation endpoints (Ray Serve only if scale need is proven).
- [ ] `DEV-00097` Online Inference - model composition graph with independent autoscaling and timeout budgets.
- [ ] `DEV-00098` Online Inference - shadow-mode scoring parity harness versus current inference path.
- [ ] `DEV-00099` Online Inference - inference contract validator (request/response schema + version pin checks).
- [ ] `DEV-00130` Control Panel (P3) - feature platform module (feature views, online/offline status, skew/parity health, version controls).
- [ ] `DEV-00132` Control Panel (P3) - online inference module (deployment topology, scaling/time budgets, shadow parity monitors).

### Priority 4 — Trading Control Plane (Safety Before ML)

- [ ] `DEV-00100` Risk & Portfolio Control - full hard-limit coverage matrix (pre-trade, drawdown, concentration, liquidity, kill-switch scenarios).
- [ ] `DEV-00101` Risk & Portfolio Control - portfolio/risk reconciliation stress harness for rapid fill bursts and cross-symbol exposure shocks.
- [ ] `DEV-00102` Risk & Portfolio Control - fail-closed recovery choreography when risk service health is degraded or uncertain.
- [ ] `DEV-00148` Risk & Portfolio Control - deterministic policy engine contract (instrument/strategy/broker/account limit composition and precedence).
- [ ] `DEV-00133` Control Panel (P4) - risk/portfolio module expansion (policy matrix editor, stress controls, fail-closed posture dashboard).

### Priority 5 — Execution

- [ ] `DEV-00103` Execution Layer - broker lifecycle + idempotency/state-machine conformance suite (submit/amend/cancel/partial/reject/expire/reconcile + duplicate/out-of-order stream handling).
- [ ] `DEV-00104` Execution Layer - resilient retry/timeout policy tuning with venue-specific failure taxonomies and SLA evidence.
- [ ] `DEV-00105` Execution Layer - reconciliation autopilot for orphan orders/fills and deterministic conflict resolution.
- [ ] `DEV-00134` Control Panel (P5) - execution module expansion (lifecycle conformance monitor, retry/timeout controls, reconciliation cockpit).

### Priority 6 — Observability and Intelligence Foundation

- [ ] `DEV-00112` Observability/Audit/Governance - OpenTelemetry end-to-end trace propagation across all runtime services.
- [ ] `DEV-00113` Observability/Audit/Governance - Prometheus metrics standardization and per-service SLO dashboard pack.
- [ ] `DEV-00114` Observability/Audit/Governance - alert routing + escalation policy with incident runbook bindings and evidence capture.
- [ ] `DEV-00115` Observability/Audit/Governance - full decision lineage explorer linking market event -> feature -> inference -> risk -> execution -> journal.
- [ ] `DEV-00136` Control Panel (P6) - observability/governance module expansion (trace lineage, SLO registry, alert-routing policy controls).

### Priority 7 — MLflow and Feature Maturity

- [ ] `DEV-00095` Research/Validation - model promotion gate + MLflow lineage/comparison hardening (signatures, benchmark thresholds, approval audit, deterministic evidence).

### Priority 8 — RAG + LLM Analyst (Advisory Only, Last)

- [ ] `DEV-00106` AI Reasoning & Memory - retrieval service baseline (document ingestion, chunking, indexing, relevance filters).
- [ ] `DEV-00107` AI Reasoning & Memory - vector-store contract rollout (pgvector-first schema/index and query path hardening).
- [ ] `DEV-00108` AI Reasoning & Memory - prompt/context builder with strict schema-bound output contracts and rejection handling.
- [ ] `DEV-00109` AI Reasoning & Memory - LLM analyst runtime with advisory-only enforcement and deterministic boundary checks.
- [ ] `DEV-00110` AI Reasoning & Memory - LLM critic/reviewer workflow for contradiction detection and policy-conformance scoring.
- [ ] `DEV-00111` AI Reasoning & Memory - seven-artifact governance completion pack (rulebook, scenarios, output schema, taxonomy, benchmark, prompt contract closures).
- [ ] `DEV-00135` Control Panel (P8) - AI reasoning module (retrieval/index ops, prompt/contract governance, analyst/critic visibility).

### Cross-Cutting Platform and Security

- [ ] `DEV-00066` Program Governance - architecture traceability matrix linking every Section 5 responsibility to code path, test gate, and runbook evidence.
- [ ] `DEV-00116` Platform Topology - Kubernetes deployment baseline (namespaces, workloads, config/secret contracts) for all Section 5 services.
- [ ] `DEV-00117` Platform Topology - HA posture rollout for Kafka/Timescale/execution/risk critical path with failover drills.
- [ ] `DEV-00118` Platform Topology - environment parity pack (dev/paper/prod) with reproducible config-diff validation.
- [ ] `DEV-00119` Security & Control Boundaries - service-to-service authN/authZ enforcement across all internal APIs and event producers.
- [ ] `DEV-00120` Security & Control Boundaries - immutable audit-log integrity checks and tamper-evidence verification.
- [ ] `DEV-00121` Security & Control Boundaries - production promotion approval workflow for model/LLM artifacts with RBAC + dual control.
- [ ] `DEV-00137` Control Panel - platform topology module (Kubernetes workload/environment parity views and guarded deployment/config actions).
- [ ] `DEV-00138` Control Panel - security controls module (service auth policy center, audit-integrity checks, dual-approval governance console).
- [ ] `DEV-00151` Control Panel Foundation - unified configuration registry core (typed schema, validation engine, RBAC/approval/rollback primitives).
- [ ] `DEV-00152` Control Panel Foundation - configuration registry adoption rollout across all modules with migration and compatibility checks.

### Final Completion

- [ ] `DEV-00067` Program Governance - final readiness gate aggregator (`make test-section-5-complete`) with deterministic pass/fail summary.
- [ ] `DEV-00122` Final Completion - full Section 5 replay/paper/live readiness evidence bundle and final `100%` closure report.
- [ ] `DEV-00140` Control Panel Finalization - end-to-end UX/RBAC/audit consistency pass across all control-panel modules with completion evidence.

## In Progress

- [ ] `DEV-00155` Ingestion->Charting clockwork reliability epic (end-to-end deterministic reliability closure program).
- [ ] `DEV-00156` Clockwork loop reliability gate and burn-in harness (objective pass/fail for cycle reliability).

## Done

- [x] Initialized NITRA git repository and created baseline initial commit.
- [x] Split ruleset responsibilities into global (`docs/ruleset.md`) and ingestion domain (`docs/design/ingestion/ruleset.md`).
- [x] Created development workspace and registered `DEV-00001` program scope.
- [x] `DEV-00002` ingestion reuse mapping (`../barsfp` -> `nitra`) with strict reject list.
- [x] `DEV-00003` Kafka contracts and topic bootstrap for NITRA ingestion.
- [x] `DEV-00004` canonical ingestion schema and idempotency ledger migrations.
- [x] `DEV-00005` minimal ingestion service wire-up in compose.
- [x] `DEV-00006` replay and idempotency verification tests.
- [x] `DEV-00007` development runbook for live ingestion startup/validation.
- [x] Reorganized `docs/` into a unified documentation entrypoint and coherent cross-link structure.
- [x] Embedded mandatory "Where are we?" status protocol in rulesets and memory operating model.
- [x] ADR/HLD/LLD policy baseline for Section 5.1 runtime allocation and boundaries.
- [x] Section 5.1 hard-gate technology enforcement rollout (`make enforce-section-5-1`).
- [x] `DEV-00010` Rust migration for market ingestion connectors.
- [x] `DEV-00011` Rust migration for market normalization/replay.
- [x] `DEV-00012` Rust migration for bar/gap/backfill controller.
- [x] `DEV-00013` enforce startup 90-day `1m` coverage and missing-only backfill for all active instruments (closed with live runtime evidence on 2026-04-26).
- [x] `DEV-00014` implement venue-history adapters and session-aware continuity policy for 90-day backfill (closed with live runtime evidence on 2026-04-26).
- [x] Implement replay controller to consume `replay.commands`.
- [x] `DEV-00015` chart interaction UX parity upgrade (15 interaction features).
- [x] `DEV-00018` deterministic `structure-engine` runtime baseline (Rust service + Kafka contracts + persisted structure state).
- [x] `DEV-00019` deterministic `risk-engine` runtime baseline (Rust service + deterministic policy checks + persisted risk state/audit).
- [x] `DEV-00020` deterministic `execution-gateway` baseline and audit/journal persistence contract.
- [x] `DEV-00021` broker-venue adapter layer for `execution-gateway` (submit/amend/cancel + ack/fill ingest).
- [x] `DEV-00023` deterministic portfolio-state baseline and richer risk constraints (`portfolio-engine` + portfolio-aware risk caps).
- [x] `DEV-00025` control panel foundation shell and design system (FastAPI route + professional black/white sidebar admin shell baseline).
- [x] `DEV-00026` control panel authentication, RBAC, and operator identity baseline (token auth, role guards, privileged-action audit trail).
- [x] `DEV-00027` control panel market ingestion and data quality operations center (connector matrix, coverage/recovery visibility, guarded backfill action).
- [x] `DEV-00028` control panel strategy/risk/portfolio control center (live posture views, risk-limit editor, kill-switch controls, audited mutations).
- [x] `DEV-00029` control panel execution OMS and broker operations center (order blotter, command workflows, reconciliation queue, broker diagnostics).
- [x] `DEV-00030` control panel charting workbench integration (instrument profile API, split-view chart workspace, cross-module one-click handoff).
- [x] `DEV-00031` control panel alerting, incidents, and runbooks center (alert inbox lifecycle actions, incident workspace, runbook execution audit contract).
- [x] `DEV-00032` control panel research/backtesting/model-ops center (dataset lineage registry, backtest launcher/history, model promotion gate with audit trail).
- [x] `DEV-00033` control panel config registry/change-control/governance center (typed registry, proposal/approve/apply/rollback flow, immutable history + audit trail).
- [x] `DEV-00034` control panel enterprise polish/performance/accessibility (command palette, persisted layout/density, focus/keyboard semantics, bounded render slices).
- [x] `DEV-00022` execution adapter network resilience (deterministic retry/backoff, failure-classified terminal outcomes, degraded-mode safeguards, reconciliation context).
- [x] `DEV-00024` control panel program epic (closed with delivery evidence map across `DEV-00025..DEV-00034`).
- [x] `DEV-00035` second-chain hardening program epic (delivery program + deterministic ticket sequence `DEV-00036..DEV-00043` finalized).
- [x] `DEV-00036` second-chain contracts and replay determinism (canonical schema baseline + replay equivalence gates + `dev-0036` test pack).
- [x] `DEV-00037` structure-engine production deterministic hardening (invariant guards, replay ordering protection, transition-reason persistence, `dev-0037` pack).
- [x] `DEV-00038` feature service deterministic baseline and point-in-time integrity (Python feature-service baseline, PIT-safe transforms, lineage persistence, `dev-0038` pack).
- [x] `DEV-00039` signal engine deterministic scorer and explainability baseline (deterministic scoring contract, explainability payloads, calibration harness, `dev-0039` pack).
- [x] `DEV-00040` risk policy expansion and decision traceability hardening (canonical policy IDs, evaluation traces, stress suite, `dev-0040` pack).
- [x] `DEV-00041` execution lifecycle controls and reconciliation SLA hardening (lifecycle guards, stale/duplicate command controls, SLA context, `dev-0041` pack).
- [x] `DEV-00042` portfolio authoritative reconciliation and state invariants (reconciliation invariants, drift taxonomy, persistence evidence, `dev-0042` pack).
- [x] `DEV-00045` control-panel target architecture and migration contract freeze (LLD architecture freeze, migration map, compatibility matrix, `dev-0045` pack).
- [x] `DEV-00046` control-panel backend modularization foundation and service rename (new `services/control-panel` skeleton, compose service rename, legacy bridge, `dev-0046` pack).
- [x] `DEV-00047` control-panel domain router split and service-layer extraction (domain routers + service proxy bridge + `dev-0047` pack).
- [x] `DEV-00048` control-panel charting module extraction and compatibility bridge (dedicated charting router + compatibility alias/deprecation headers + `dev-0048` pack).
- [x] `DEV-00049` control-panel frontend app-shell restructure and UI architecture hardening (source/dist frontend boundary + extracted css/js modules + `dev-0049` pack).
- [x] `DEV-00050` control-panel refactor quality gates and CI readiness (aggregate backend/frontend/compat gates + CI-ready command + `dev-0050` pack).
- [x] `DEV-00051` control-panel refactor rollout, cutover, and deprecation closure (native charting cutover + rollout/rollback runbook + deprecation report + `dev-0051` pack).
- [x] `DEV-00052` reconciliation/runbook evidence capture expansion for live adapter behavior (runbook-linked adapter evidence snapshots + reconciliation evidence contract + `dev-0052` pack).
- [x] `DEV-00053` control-panel ingestion KPI monitor (130k 1m-ohlcv target tracking + raw-tick realtime SLA monitor + `dev-0053` pack).
- [x] `DEV-00054` chart liquidity-structure layer toggle (checkbox-enabled pullback/minor/major overlay model on any instrument + `dev-0054` pack).
- [x] `DEV-00055` interpretation-governance architecture pack (HLD integration + dedicated LLD for ontology/rulebook/scenarios/schema/taxonomy/benchmark/prompt-contract).
- [x] `DEV-00056` canonical liquidity ontology baseline + chart legend clarity (project-wide ontology doc + explicit in-layer semantic legend + `dev-0055` pack).
- [x] `DEV-00044` control-panel service refactor program epic (monolith-to-modular production architecture) closed after completion of `DEV-00045..DEV-00051`; reconciliation/status-normalization tracked by `DEV-00057`.
- [x] `DEV-00057` control-panel program reconciliation and closure hygiene (status normalization completed across Kanban + memory artifacts in same session).
- [x] `DEV-00063` control-panel post-cutover observability revalidation (live sustained-load evidence captured; route parity fix applied for `/api/v1/charting/markets/available`).
- [x] `DEV-00064` next roadmap slice definition completed (feature-platform shadow-readiness ticket registered with acceptance criteria and verification target `test-dev-0064`).
- [x] `DEV-00065` deterministic-first governance deliverables completed (dependency map + closure criteria artifacts + `test-dev-0065` verification target).
- [x] `DEV-00068` connector failover policy contract delivered with operator-managed policy persistence + audit path (`/api/v1/control-panel/ingestion/failover-policy`, `test-dev-0068`).
- [x] `DEV-00124` control-panel feeds ops failover controls delivered (policy table/runtime metrics + guarded update form in ingestion workspace).
- [x] `DEV-00069` credential/session lifecycle hardening delivered (session policy contract, guarded update endpoint, runtime visibility, `test-dev-0069`).
- [x] `DEV-00141` websocket/session manager hardening delivered (heartbeat/stale/reconnect policy contract + control-panel policy controls, `test-dev-0069`).
- [x] `DEV-00070` exchange/broker feed quality SLA metrics delivered (latency/drop/sequence-discontinuity/heartbeat contracts in ingestion + control-panel surface, `test-dev-0070`).
- [x] `DEV-00142` rate-limit governance and adaptive throttling policy delivered (per-venue policy contract + guarded control-panel updates + runtime adaptive backoff/recovery, `test-dev-0142`).
- [x] `DEV-00143` raw message capture conformance delivered (untouched payload persistence + sequence provenance checks + control-panel ops visibility, `test-dev-0143`).
- [x] `DEV-00071` raw data lake canonical partition/object-key strategy delivered (deterministic parquet key contract + replay-grade manifest provenance + control-panel ops visibility, `test-dev-0071`).
- [x] `DEV-00072` replay manifest/index service delivered (deterministic range selection index + checksum provenance + control-panel build workflow, `test-dev-0072`).
- [x] `DEV-00073` raw data lake retention/tiering/restore runbook delivered with validation evidence for dev/staging/prod.
- [x] `DEV-00074` Kafka topic-level SLO and partition/retention right-sizing policy delivered with enforcement checks.
- [x] `DEV-00075` Kafka consumer lag recovery automation and dead-letter replay workflow hardening delivered.
- [x] `DEV-00076` Kafka schema compatibility CI gate delivered for backward/forward validation across runtime topics.
- [x] `DEV-00077` normalization/replay deterministic quarantine pipeline delivered with replay-safe re-ingest flow (`test-dev-0077`).
- [x] `DEV-00078` normalization/replay sequence/order integrity verifier delivered across source-stream sequence provenance and normalized output ordering (`test-dev-0078`).
- [x] `DEV-00125` control-panel P0 raw data lake module delivered (partition browser, replay manifest, retention controls).
- [x] `DEV-00126` control-panel P0 Kafka module delivered (topic SLOs, lag recovery controls, partition/retention management).
- [x] `DEV-00153` control-panel root routing + chart-tab handoff delivered (`/` now serves control panel, chart launches moved to new-tab flow with instrument-aware/default fallback).
- [x] `DEV-00154` liquidity-layer backend projection delivered (ontology-derived today+yesterday closed-`M5` API + chart consumption replacing local heuristic overlay path).
- [x] `DEV-00139` control-panel unified configuration registry super-scope retired (split into `DEV-00151` core + `DEV-00152` adoption rollout).
- [x] `DEV-00149` execution idempotency/state-machine conformance standalone scope retired (merged into `DEV-00103`).
- [x] `DEV-00150` MLflow lineage/comparison standalone scope retired (merged into `DEV-00095`).

## Blocked

- [ ] (No blocked items)
