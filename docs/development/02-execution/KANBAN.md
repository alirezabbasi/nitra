# NITRA Project Kanban

Last updated: 2026-04-23

## Backlog

- [ ] Define and approve next program ticket set beyond ingestion baseline.
- [ ] Implement deterministic `structure-engine` runtime baseline.
- [ ] Implement deterministic `risk-engine` runtime baseline.
- [ ] Implement `execution-gateway` runtime baseline with order-state machine.
- [ ] Implement replay controller to consume `replay.commands`.
- [ ] Implement project-wide audit/journal event persistence contract.

## In Progress

- [ ] Define next program ticket set beyond ingestion baseline.

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

## Blocked

- [ ] (No blocked items)
