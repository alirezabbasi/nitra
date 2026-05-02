CREATE TABLE IF NOT EXISTS raw_lake_retention_policy (
  environment TEXT PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  hot_retention_days INTEGER NOT NULL DEFAULT 14,
  warm_retention_days INTEGER NOT NULL DEFAULT 90,
  cold_retention_days INTEGER NOT NULL DEFAULT 365,
  archive_tier TEXT NOT NULL DEFAULT 'standard',
  restore_sla_minutes INTEGER NOT NULL DEFAULT 120,
  validation_interval_hours INTEGER NOT NULL DEFAULT 24,
  updated_by TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_raw_lake_retention_env
    CHECK (environment IN ('dev', 'staging', 'prod')),
  CONSTRAINT chk_raw_lake_retention_order
    CHECK (hot_retention_days >= 1 AND warm_retention_days >= hot_retention_days AND cold_retention_days >= warm_retention_days),
  CONSTRAINT chk_raw_lake_restore_sla
    CHECK (restore_sla_minutes >= 1 AND restore_sla_minutes <= 10080),
  CONSTRAINT chk_raw_lake_validation_interval
    CHECK (validation_interval_hours >= 1 AND validation_interval_hours <= 720)
);

CREATE TABLE IF NOT EXISTS raw_lake_restore_validation_log (
  drill_id UUID PRIMARY KEY,
  environment TEXT NOT NULL,
  window_from_ts TIMESTAMPTZ NOT NULL,
  window_to_ts TIMESTAMPTZ NOT NULL,
  object_count_checked INTEGER NOT NULL DEFAULT 0,
  row_count_checked BIGINT NOT NULL DEFAULT 0,
  checksum_match BOOLEAN NOT NULL DEFAULT FALSE,
  restore_duration_seconds INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  notes TEXT,
  executed_by TEXT NOT NULL,
  executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_raw_lake_restore_env
    CHECK (environment IN ('dev', 'staging', 'prod')),
  CONSTRAINT chk_raw_lake_restore_window
    CHECK (window_to_ts >= window_from_ts),
  CONSTRAINT chk_raw_lake_restore_status
    CHECK (status IN ('completed', 'failed', 'warning'))
);

CREATE INDEX IF NOT EXISTS idx_raw_lake_restore_validation_log_executed_at
  ON raw_lake_restore_validation_log (executed_at DESC);

INSERT INTO raw_lake_retention_policy (
  environment,
  enabled,
  hot_retention_days,
  warm_retention_days,
  cold_retention_days,
  archive_tier,
  restore_sla_minutes,
  validation_interval_hours,
  updated_by
)
VALUES
  ('dev', TRUE, 14, 90, 365, 'standard', 120, 24, 'seed'),
  ('staging', TRUE, 14, 90, 365, 'standard', 120, 24, 'seed'),
  ('prod', TRUE, 14, 90, 365, 'standard', 120, 24, 'seed')
ON CONFLICT (environment) DO NOTHING;
