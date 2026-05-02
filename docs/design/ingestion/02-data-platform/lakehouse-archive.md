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

## Canonical Parquet Partitioning + Object Key Contract (DEV-00071)

- Raw-capture archive objects use canonical partitioned keys:
  - `raw_capture/format=parquet/venue=<venue>/topic=<topic>/partition=<partition>/symbol=<symbol>/year=YYYY/month=MM/day=DD/hour=HH/capture.parquet`
- Manifest contract (`raw_lake_object_manifest`) records replay-grade provenance per object:
  - `source_topic`, `source_partition`
  - `min_source_offset`, `max_source_offset`
  - `first_event_ts_received`, `last_event_ts_received`
  - `row_count`
- Object-key generation is deterministic for identical `(venue,symbol,topic,partition,hour)` input windows.

## Replay Manifest/Index Contract (DEV-00072)

- Replay manifest selection uses deterministic object ordering:
  - ordered by `(partition_year, partition_month, partition_day, partition_hour, object_key)`.
- Replay manifest index contract (`raw_lake_replay_manifest_index`) persists:
  - selection range (`range_from_ts`, `range_to_ts`),
  - selected object key list (`object_keys`),
  - deterministic provenance summary (`object_count`, `selected_row_count`, `min_source_offset`, `max_source_offset`),
  - integrity checksum (`checksum_sha256`) computed from ordered object keys.
- Control-plane build endpoint:
  - `POST /api/v1/control-panel/ingestion/raw-lake/replay-manifest`

## Retention/Tiering + Restore Validation Contract (DEV-00073)

- Retention policy contract (`raw_lake_retention_policy`) is environment-scoped (`dev`, `staging`, `prod`) and enforces ordered hot/warm/cold windows.
- Restore drill evidence contract (`raw_lake_restore_validation_log`) captures deterministic validation windows, object/row counts, checksum match status, and restore duration evidence.
- Control-plane mutation endpoints:
  - `POST /api/v1/control-panel/ingestion/raw-lake/retention-policy`
  - `POST /api/v1/control-panel/ingestion/raw-lake/restore-drill`
