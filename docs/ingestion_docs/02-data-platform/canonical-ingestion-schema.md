# Canonical Ingestion Schema (NITRA Dev Baseline)

This schema baseline covers the minimum persistence required for ingestion and replay-safe processing in NITRA dev.

## Scope

Included entities:
- `ohlcv_bar`
- `processed_message_ledger`
- `raw_tick`
- `trade_print`
- `book_event`

## Migration Files

- `infra/timescaledb/init/001_ohlcv_bar.sql`
- `infra/timescaledb/init/002_processed_message_ledger.sql`
- `infra/timescaledb/init/003_market_event_entities.sql`

## Idempotency Contract

`processed_message_ledger` enforces dedupe/replay guards with:
- primary key on `(service_name, message_id)`
- uniqueness on `(service_name, source_topic, source_partition, source_offset)`

Expected consumer behavior:
1. decode and validate
2. skip if message already processed
3. execute side effects
4. write ledger row
5. commit offset

## Notes

- This baseline intentionally excludes non-essential tables and compatibility views.
- Tables are designed for ingestion correctness first, with room for expansion in later tickets.
