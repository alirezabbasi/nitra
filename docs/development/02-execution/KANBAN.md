# NITRA Project Kanban

Last updated: 2026-04-30

## Backlog

- [ ] `DEV-00065` Component: Program Governance - Section 5 final-completion program map, dependency graph, and closure criteria (`100%` exit contract).
- [ ] `DEV-00066` Component: Program Governance - architecture traceability matrix linking every Section 5 component responsibility to code path, test gate, and runbook evidence.
- [ ] `DEV-00067` Component: Program Governance - final readiness gate aggregator (`make test-section-5-complete`) with deterministic pass/fail summary.
- [ ] `DEV-00068` Component: Exchange/Broker Feeds - connector failover policy per venue (endpoint rotation, retry tiers, circuit-open thresholds).
- [ ] `DEV-00069` Component: Exchange/Broker Feeds - credential/session lifecycle hardening (token refresh, expiration guardrails, auth error classification).
- [ ] `DEV-00070` Component: Exchange/Broker Feeds - inbound feed quality SLA metrics (latency, drop, sequence discontinuity, venue heartbeat).
- [ ] `DEV-00071` Component: Raw Data Lake - canonical Parquet partitioning and object-key strategy for replay-grade raw archives.
- [ ] `DEV-00072` Component: Raw Data Lake - replay manifest/index service for deterministic range selection and provenance checks.
- [ ] `DEV-00073` Component: Raw Data Lake - retention/tiering/restore runbook with validation evidence for dev/staging/prod.
- [ ] `DEV-00074` Component: Kafka Backbone - topic-level SLO and partition/retention right-sizing policy with enforcement checks.
- [ ] `DEV-00075` Component: Kafka Backbone - consumer lag recovery automation and dead-letter replay workflow hardening.
- [ ] `DEV-00076` Component: Kafka Backbone - schema compatibility CI gate for backward/forward validation across all runtime topics.
- [ ] `DEV-00077` Component: Normalization/Replay - deterministic quarantine pipeline for malformed events with replay-safe re-ingest flow.
- [ ] `DEV-00078` Component: Normalization/Replay - sequence/order integrity verifier across venue streams and normalized outputs.
- [ ] `DEV-00079` Component: Normalization/Replay - full 90-day startup-coverage conformance harness with venue-session edge-case fixtures.
- [ ] `DEV-00080` Component: Deterministic Structure Engine - rulebook-complete implementation audit (inside/outside/pullback/minor/major edge paths).
- [ ] `DEV-00081` Component: Deterministic Structure Engine - state snapshot versioning and deterministic migration harness for long-horizon replay stability.
- [ ] `DEV-00082` Component: Deterministic Structure Engine - structure regression benchmark pack (historical fixture library + invariants report).
- [ ] `DEV-00083` Component: Time-Series Storage - continuous aggregate/materialization strategy for operational and research query workloads.
- [ ] `DEV-00084` Component: Time-Series Storage - compression/retention policy rollout with deterministic restore verification.
- [ ] `DEV-00085` Component: Time-Series Storage - schema/index performance hardening under sustained replay and live ingest concurrency.
- [ ] `DEV-00086` Component: Feature Platform (Feast) - bootstrap feature repository and registry contracts aligned to existing feature-service outputs.
- [ ] `DEV-00087` Component: Feature Platform (Feast) - online store integration and retrieval APIs for low-latency inference consumption.
- [ ] `DEV-00088` Component: Feature Platform (Feast) - offline store and point-in-time dataset materialization pipeline.
- [ ] `DEV-00089` Component: Feature Platform (Feast) - training-serving skew detection gates and parity assertions in CI.
- [ ] `DEV-00090` Component: Feature Platform (Feast) - feature versioning/deprecation policy with backfill-safe migration workflow.
- [ ] `DEV-00091` Component: Research/Backtesting - deterministic dataset builder pipeline with reproducible snapshot manifests.
- [ ] `DEV-00092` Component: Research/Backtesting - walk-forward validator framework and baseline evaluation scenarios.
- [ ] `DEV-00093` Component: Research/Backtesting - labeling framework contracts and quality validation for supervised pipelines.
- [ ] `DEV-00094` Component: Research/Backtesting - experiment runner orchestration with standardized metric and artifact capture.
- [ ] `DEV-00095` Component: Research/Backtesting - model promotion gate linking MLflow signatures, benchmark thresholds, and approval audit.
- [ ] `DEV-00096` Component: Online Inference (Ray Serve) - baseline Ray Serve deployment integrating signal/regime/aggregation endpoints.
- [ ] `DEV-00097` Component: Online Inference (Ray Serve) - model composition graph with independent autoscaling and timeout budgets.
- [ ] `DEV-00098` Component: Online Inference (Ray Serve) - shadow-mode scoring parity harness versus current inference path.
- [ ] `DEV-00099` Component: Online Inference (Ray Serve) - inference contract validator (request/response schema + version pin checks).
- [ ] `DEV-00100` Component: Risk & Portfolio Control - full hard-limit coverage matrix (pre-trade, drawdown, concentration, liquidity, kill-switch scenarios).
- [ ] `DEV-00101` Component: Risk & Portfolio Control - portfolio/risk reconciliation stress harness for rapid fill bursts and cross-symbol exposure shocks.
- [ ] `DEV-00102` Component: Risk & Portfolio Control - fail-closed recovery choreography when risk service health is degraded or uncertain.
- [ ] `DEV-00103` Component: Execution Layer - broker lifecycle conformance suite (submit/amend/cancel/partial/reject/expire/reconcile paths).
- [ ] `DEV-00104` Component: Execution Layer - resilient retry/timeout policy tuning with venue-specific failure taxonomies and SLA evidence.
- [ ] `DEV-00105` Component: Execution Layer - reconciliation autopilot for orphan orders/fills and deterministic conflict resolution.
- [ ] `DEV-00106` Component: AI Reasoning & Memory - retrieval service baseline (document ingestion, chunking, indexing, relevance filters).
- [ ] `DEV-00107` Component: AI Reasoning & Memory - vector-store contract rollout (pgvector-first schema/index and query path hardening).
- [ ] `DEV-00108` Component: AI Reasoning & Memory - prompt/context builder with strict schema-bound output contracts and rejection handling.
- [ ] `DEV-00109` Component: AI Reasoning & Memory - LLM analyst runtime with advisory-only enforcement and deterministic boundary checks.
- [ ] `DEV-00110` Component: AI Reasoning & Memory - LLM critic/reviewer workflow for contradiction detection and policy-conformance scoring.
- [ ] `DEV-00111` Component: AI Reasoning & Memory - seven-artifact governance completion pack (rulebook, scenarios, output schema, taxonomy, benchmark, prompt contract closures).
- [ ] `DEV-00112` Component: Observability/Audit/Governance - OpenTelemetry end-to-end trace propagation across all runtime services.
- [ ] `DEV-00113` Component: Observability/Audit/Governance - Prometheus metrics standardization and per-service SLO dashboard pack.
- [ ] `DEV-00114` Component: Observability/Audit/Governance - alert routing + escalation policy with incident runbook bindings and evidence capture.
- [ ] `DEV-00115` Component: Observability/Audit/Governance - full decision lineage explorer linking market event -> feature -> inference -> risk -> execution -> journal.
- [ ] `DEV-00116` Component: Platform Topology - Kubernetes deployment baseline (namespaces, workloads, config/secret contracts) for all Section 5 services.
- [ ] `DEV-00117` Component: Platform Topology - HA posture rollout for Kafka/Timescale/execution/risk critical path with failover drills.
- [ ] `DEV-00118` Component: Platform Topology - environment parity pack (dev/paper/prod) with reproducible config-diff validation.
- [ ] `DEV-00119` Component: Security & Control Boundaries - service-to-service authN/authZ enforcement across all internal APIs and event producers.
- [ ] `DEV-00120` Component: Security & Control Boundaries - immutable audit-log integrity checks and tamper-evidence verification.
- [ ] `DEV-00121` Component: Security & Control Boundaries - production promotion approval workflow for model/LLM artifacts with RBAC + dual control.
- [ ] `DEV-00122` Component: Final Completion - full Section 5 replay/paper/live readiness evidence bundle and final `100%` closure report.

## In Progress

- [ ] (No active items)

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

## Blocked

- [ ] (No blocked items)
