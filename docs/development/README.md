# NITRA Development Workspace

This folder tracks implementation planning and execution tickets for NITRA development work.

## Purpose

- Keep development work items explicit, scoped, and traceable.
- Keep implementation aligned with:
  - `docs/ruleset.md` (global governance)
  - `docs/design/nitra_system_hld.md` and `docs/design/AI-enabled_trading_decision_platform.md` (architecture authority)
  - relevant domain ruleset/docs when applicable

## Ticketing Rules

- Ticket IDs use `DEV-XXXXX` format.
- Each ticket must include scope, non-goals, acceptance criteria, and HLD alignment notes.
- Keep dev environment changes simple and reproducible in Docker Compose.
- Avoid adding non-essential complexity in the baseline dev stack.

## Tickets

- [DEV-00001](/home/alireza/Projects/nitra/docs/development/tickets/DEV-00001-barsfp-ingestion-wireup.md): Wire reusable BarsFP ingestion components into NITRA with a simple dev environment.
- [DEV-00002](/home/alireza/Projects/nitra/docs/development/tickets/DEV-00002-ingestion-reuse-map.md): Create strict reuse map with `reuse/adapt/reject` decisions.
- [DEV-00003](/home/alireza/Projects/nitra/docs/development/tickets/DEV-00003-kafka-contract-bootstrap.md): Add minimal Kafka topic contract and bootstrap.
- [DEV-00004](/home/alireza/Projects/nitra/docs/development/tickets/DEV-00004-ingestion-schema-ledger.md): Add canonical ingestion schema and idempotency ledger.
- [DEV-00005](/home/alireza/Projects/nitra/docs/development/tickets/DEV-00005-minimal-service-wireup.md): Wire minimum ingestion services into NITRA compose.
- [DEV-00006](/home/alireza/Projects/nitra/docs/development/tickets/DEV-00006-replay-idempotency-tests.md): Add replay/idempotency verification tests.
- [DEV-00007](/home/alireza/Projects/nitra/docs/development/tickets/DEV-00007-dev-runbook-live-ingest.md): Document dev runbook for live ingestion operations.

## Project Tracking

- [Kanban TODO Board](/home/alireza/Projects/nitra/docs/development/TODO.md)
