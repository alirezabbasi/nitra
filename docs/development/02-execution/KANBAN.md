# NITRA Project Kanban

Last updated: 2026-04-29

## Backlog

- [x] `DEV-00043` journal/audit evidence fabric and incident bundle export.
- [ ] Re-validate control-panel post-cutover observability thresholds under sustained runtime load.

## In Progress

- [ ] `DEV-00044` control-panel service refactor program epic (monolith-to-modular production architecture).

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

## Blocked

- [ ] (No blocked items)
