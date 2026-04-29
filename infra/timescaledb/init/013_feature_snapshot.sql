CREATE TABLE IF NOT EXISTS feature_snapshot (
  feature_id UUID PRIMARY KEY,
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  event_ts TIMESTAMPTZ NOT NULL,
  bucket_start TIMESTAMPTZ NOT NULL,
  feature_set_version TEXT NOT NULL,
  features JSONB NOT NULL,
  lineage JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (venue, canonical_symbol, timeframe, bucket_start, feature_set_version)
);

CREATE INDEX IF NOT EXISTS idx_feature_snapshot_symbol_ts
  ON feature_snapshot (venue, canonical_symbol, timeframe, event_ts DESC);

CREATE INDEX IF NOT EXISTS idx_feature_snapshot_lineage_source
  ON feature_snapshot ((lineage->>'source_topic'), ((lineage->>'source_partition')::int), ((lineage->>'source_offset')::bigint));
