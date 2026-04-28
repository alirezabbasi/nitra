# NITRA Project Kanban

Last updated: 2026-04-29

## Backlog

- [ ] Expand reconciliation/runbook evidence capture for live adapter behavior.
- [ ] `DEV-00024` control panel program epic (professional admin console, black-and-white shadcn design language).
- [ ] `DEV-00032` control panel research/backtesting/model-ops center.
- [ ] `DEV-00033` control panel config registry, change control, and governance.
- [ ] `DEV-00034` control panel enterprise polish, performance, and accessibility.

## In Progress

- [ ] `DEV-00022` execution adapter network resilience (DNS/connectivity/runtime robustness).

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

## Blocked

- [ ] (No blocked items)
