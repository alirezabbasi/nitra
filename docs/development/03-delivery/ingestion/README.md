# Ingestion Delivery Index

This index summarizes delivered ingestion baseline work and links to source tickets/evidence.

## Program ticket

- `DEV-00001`: `docs/development/tickets/DEV-00001-barsfp-ingestion-wireup.md`

## Supporting tickets

- `DEV-00002`: `docs/development/tickets/DEV-00002-ingestion-reuse-map.md`
- `DEV-00003`: `docs/development/tickets/DEV-00003-kafka-contract-bootstrap.md`
- `DEV-00004`: `docs/development/tickets/DEV-00004-ingestion-schema-ledger.md`
- `DEV-00005`: `docs/development/tickets/DEV-00005-minimal-service-wireup.md`
- `DEV-00006`: `docs/development/tickets/DEV-00006-replay-idempotency-tests.md`
- `DEV-00007`: `docs/development/tickets/DEV-00007-dev-runbook-live-ingest.md`

## Key artifacts

- Reuse map: `docs/development/03-delivery/ingestion/artifacts/DEV-00002-reuse-map.md`
- Runbook: `docs/development/03-delivery/ingestion/artifacts/DEV-00007-live-ingestion-runbook.md`
- Tests: `tests/dev-00003`, `tests/dev-00004`, `tests/dev-00005`, `tests/dev-00006`, `tests/dev-00008`
- Runtime services: `services/market-ingestion`, `services/market-normalization`, `services/bar-aggregation`, `services/gap-detection`, `services/backfill-worker`, `services/charting`

## Completion status

Ingestion baseline: `completed` for current planned ticket set (`DEV-00001..DEV-00007`).
