# Data Platform Contracts

## Canonical Event Schema (Required Fields)

- `event_id` (UUID)
- `venue`
- `asset_class`
- `broker_symbol`
- `canonical_symbol`
- `event_type` (`tick|trade|quote|bar_close|health`)
- `event_ts_exchange`
- `event_ts_received`
- `price_fields` (`bid`, `ask`, `mid`, `last` as available)
- `volume`
- `sequence_id` (nullable)
- `source_checksum`
- `ingestion_run_id`
- `schema_version`

## Redpanda Topic Taxonomy

- `raw.market.<venue>`
- `normalized.tick.<asset_class>`
- `normalized.trade.<asset_class>`
- `normalized.quote.<asset_class>`
- `bar.1s`
- `bar.1m`
- `bar.5m`
- `bar.1h`
- `gap.events`
- `risk.events`
- `execution.orders`
- `execution.fills`
- `connector.health`

## TimescaleDB (Hot)

Retention target: rolling 90 days for operational workflows.

Core tables:
- `events_recent`
- `bars_1s_recent`
- `ohlcv_bar`
- `raw_tick`
- `book_event`
- `trade_print`
- `gap_log`
- `ingestion_offsets`
- `risk_decisions`
- `orders_recent`
- `fills_recent`

Continuous aggregates:
- `bars_5m_recent`
- `bars_15m_recent`
- `bars_1h_recent`
- `bars_4h_recent`
- `bars_1d_recent`

## ClickHouse (Cold Analytics)

Core tables:
- `events_hist`
- `bars_hist`
- `orderbook_top_hist` (optional)
- `risk_events_hist`
- `execution_hist`
- `qa_reconciliation_results`

Partition/order strategy is query-driven and version-controlled.

## MinIO / S3 Lakehouse Layout

- `s3://barsfp-lake/raw/venue=<venue>/date=YYYY-MM-DD/*.parquet`
- `s3://barsfp-lake/normalized/type=<type>/date=YYYY-MM-DD/*.parquet`
- `s3://barsfp-lake/bars/timeframe=<tf>/date=YYYY-MM-DD/*.parquet`
- `s3://barsfp-lake/replay/<job_id>/*.parquet`
- `s3://barsfp-lake/manifests/<dataset>/<date>.json`

## Lifecycle Policy

1. Ingest and normalize in stream.
2. Persist hot operational slice in TimescaleDB.
3. Archive immutable canonical slices to Parquet.
4. Load/query deep history in ClickHouse.
5. Verify row counts and checksums on every hot->archive->cold transition.
