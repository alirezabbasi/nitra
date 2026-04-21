# DEV-00001: Wire Reusable BarsFP Ingestion into NITRA (Simple Dev Env)

## Status

Done

## Summary

Evaluate and integrate reusable ingestion-market-data components from `../barsfp` into NITRA, while preserving NITRA's intentionally simple development environment and avoiding heavy monitoring stack complexity in the baseline dev profile.

## Background

- BarsFP contains working ingestion implementation across EPIC-01 to EPIC-12 and EPIC-21.
- NITRA currently has a simplified whole-platform dev scaffold and placeholder runtime services.
- The target is reuse of proven ingestion code patterns without importing BarsFP's full compose complexity (especially observability bundle) into default dev startup.

## In Scope

- Reuse candidates for NITRA ingestion path:
  - connector adapter patterns
  - normalizer pipeline
  - deterministic bar engine
  - gap detection/backfill workflow
  - canonical market event persistence (`raw_tick`, `book_event`, `trade_print`, `ohlcv_bar`)
  - explicit consumer commit + idempotency ledger pattern
- NITRA docker-compose changes limited to minimal components required for ingestion development and end-to-end validation.
- Documentation updates under `docs/development/` and relevant ingestion docs.

## Out of Scope

- Full BarsFP monitoring stack import (Loki, Tempo, Promtail, Cadvisor, large dashboard bundles) in baseline NITRA dev environment.
- Cold analytics and archive expansion as default startup requirements.
- Production hardening changes outside ingestion wiring scope.

## HLD Alignment Check

Aligned with:
- `docs/design/nitra_system_hld.md`
- `docs/design/AI-enabled_trading_decision_platform.md`

Rationale:
- Preserves event-driven ingestion backbone.
- Preserves deterministic core and replay-safe ingestion contracts.
- Keeps separation of concerns between ingestion and advanced analytics/operations tooling.

## Deliverables

1. Reuse mapping document (source path -> NITRA target path -> action: copy/adapt/rewrite).
2. Initial ingestion service wiring in NITRA with minimal compose profile.
3. Schema and migration baseline for canonical market entities + idempotency ledger.
4. Step-scoped tests under `tests/` validating ingestion correctness and replay safety.
5. Documentation updates for setup, run, and validation flow.

## Acceptance Criteria

- NITRA dev stack remains simple to run via `docker compose up -d`.
- Ingestion flow from raw market event to canonical persistence is demonstrably working.
- Duplicate/replay behavior is guarded (no silent loss, no duplicate side effects).
- Monitoring defaults remain lightweight in baseline dev profile.
- All changes are traceable with step-based commits and updated docs.

## Evidence

- `DEV-00002` reuse mapping completed
- `DEV-00003` Kafka contract/bootstrap completed
- `DEV-00004` canonical schema + ledger completed
- `DEV-00005` minimal ingestion wire-up completed
- `DEV-00006` replay/idempotency checks completed
- `DEV-00007` dev runbook completed

## Risks

- Contract mismatch between BarsFP naming and NITRA naming conventions.
- Over-importing legacy components can increase operational burden.
- Kafka/Redpanda implementation differences may require adapter abstractions.

## Notes

Prefer phased integration:
1. Contracts + schema + topic mapping
2. Connector + normalizer
3. Bar/gap/backfill
4. Validation and docs closure
