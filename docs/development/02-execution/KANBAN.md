# NITRA Project Kanban

Last updated: 2026-04-26

## Backlog

- [ ] Implement deterministic `structure-engine` runtime baseline.
- [ ] Implement deterministic `risk-engine` runtime baseline.
- [ ] Implement `execution-gateway` runtime baseline with order-state machine.
- [ ] Implement project-wide audit/journal event persistence contract.

## In Progress

- [ ] (No in-progress items)

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

## Blocked

- [ ] (No blocked items)
