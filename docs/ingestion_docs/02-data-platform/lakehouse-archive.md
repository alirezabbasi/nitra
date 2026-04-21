# Lakehouse Archive (EPIC-07)

## Objective

Archive hot-store bars into immutable Parquet objects in the lakehouse with idempotent manifest/checkpoint tracking.

## Runtime Components

- `archive-worker` service
- `minio` object store service (S3-compatible)
- shared `lakehouse_data` volume

## Archive Workflow

1. Read checkpoint (`archive_checkpoint`) for stream.
2. Select eligible bars from `ohlcv_bar` up to configured age threshold.
3. Write deterministic Parquet object to lake path.
4. Compute SHA-256 checksum.
5. Insert manifest row (`archive_manifest`) idempotently.
6. Advance stream checkpoint to latest archived bucket.

## Data Permanence Alignment

- Archive flow is additive only.
- No deletion of hot data or archived objects in default workflow.
- Idempotency is enforced via unique object key + checkpoint progression.
