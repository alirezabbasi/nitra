CREATE TABLE IF NOT EXISTS raw_lake_object_manifest (
  object_key TEXT PRIMARY KEY,
  format TEXT NOT NULL,
  venue TEXT NOT NULL,
  broker_symbol TEXT NOT NULL,
  source_topic TEXT NOT NULL,
  source_partition INTEGER NOT NULL,
  partition_year INTEGER NOT NULL,
  partition_month INTEGER NOT NULL,
  partition_day INTEGER NOT NULL,
  partition_hour INTEGER NOT NULL,
  first_event_ts_received TIMESTAMPTZ NOT NULL,
  last_event_ts_received TIMESTAMPTZ NOT NULL,
  min_source_offset BIGINT NOT NULL,
  max_source_offset BIGINT NOT NULL,
  row_count BIGINT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_lake_manifest_partition
  ON raw_lake_object_manifest (
    venue,
    source_topic,
    source_partition,
    partition_year,
    partition_month,
    partition_day,
    partition_hour
  );
