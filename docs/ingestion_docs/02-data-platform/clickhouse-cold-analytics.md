# ClickHouse Cold Analytics (EPIC-08)

## Objective

Shift historical analytics query load away from Timescale hot store into ClickHouse cold warehouse.

## ClickHouse Schema

- `bars_hist`: historical bars table (ReplacingMergeTree)
- `archive_loaded_manifest`: loaded-object tracker for idempotent imports

Installed via:
- `infra/clickhouse/init/001_init_cold_store.sql`

## Loader Pipeline

`cold-loader` service:
1. Reads new archive manifests from Timescale.
2. Loads referenced Parquet files from lakehouse path.
3. Inserts rows into ClickHouse `bars_hist`.
4. Records loaded manifest marker in ClickHouse.
5. Advances Timescale checkpoint in `cold_loader_checkpoint`.

## Query Split

`query-api` routes:
- `/v1/bars/hot`: Timescale hot reads
- `/v1/bars/cold`: ClickHouse cold reads

This ensures operational paths and heavy historical analytics are separated.
