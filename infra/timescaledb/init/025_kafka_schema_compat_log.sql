CREATE TABLE IF NOT EXISTS control_panel_ingestion_kafka_schema_compat_log (
  check_id UUID PRIMARY KEY,
  status TEXT NOT NULL,
  checked_topics INTEGER NOT NULL,
  failure_count INTEGER NOT NULL DEFAULT 0,
  summary TEXT,
  checked_by TEXT NOT NULL,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_kafka_schema_status
    CHECK (status IN ('passed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_control_panel_kafka_schema_compat_checked_at
  ON control_panel_ingestion_kafka_schema_compat_log (checked_at DESC);
