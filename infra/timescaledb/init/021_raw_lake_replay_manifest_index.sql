CREATE TABLE IF NOT EXISTS raw_lake_replay_manifest_index (
  manifest_id UUID PRIMARY KEY,
  venue TEXT NOT NULL,
  broker_symbol TEXT NOT NULL,
  source_topic TEXT NOT NULL,
  source_partition INTEGER NOT NULL,
  range_from_ts TIMESTAMPTZ NOT NULL,
  range_to_ts TIMESTAMPTZ NOT NULL,
  object_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
  object_count INTEGER NOT NULL DEFAULT 0,
  selected_row_count BIGINT NOT NULL DEFAULT 0,
  min_source_offset BIGINT,
  max_source_offset BIGINT,
  span_from_ts TIMESTAMPTZ,
  span_to_ts TIMESTAMPTZ,
  checksum_sha256 TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_lake_replay_manifest_created_at
  ON raw_lake_replay_manifest_index (created_at DESC);
