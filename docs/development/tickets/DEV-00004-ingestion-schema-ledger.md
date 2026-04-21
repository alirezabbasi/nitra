# DEV-00004: Canonical Ingestion Schema and Idempotency Ledger

## Status

Done

## Summary

Add the minimum Timescale/Postgres schema baseline for canonical ingestion entities and replay-safe dedup ledger in NITRA.

## Scope

- Add migrations for:
  - `raw_tick`
  - `trade_print`
  - `book_event`
  - `ohlcv_bar`
  - `processed_message_ledger`
- Ensure schema aligns with NITRA naming and contract conventions.

## Hard Exclusions

- No tables that are not required by currently wired ingestion flow.
- No backward-compatibility views unless needed by active NITRA services.

## Deliverables

1. Migration files and init wiring.
2. Schema notes describing keys/indexes/idempotency behavior.
3. Verification test for migration presence and key constraints.

## Acceptance Criteria

- Fresh dev DB bootstraps schema without manual intervention.
- Dedupe ledger supports per-service replay guard semantics.
- Canonical market entities support ingestion + query validation path.

## Evidence

- Migrations: `infra/timescaledb/init/001_ohlcv_bar.sql`, `002_processed_message_ledger.sql`, `003_market_event_entities.sql`
- Init wiring: `docker-compose.yml` (`/docker-entrypoint-initdb.d` mount)
- Schema notes: `docs/ingestion_docs/02-data-platform/canonical-ingestion-schema.md`
- Verification: `tests/dev-00004/run.sh`
