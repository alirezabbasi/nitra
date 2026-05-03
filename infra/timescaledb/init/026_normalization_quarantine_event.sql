CREATE TABLE IF NOT EXISTS normalization_quarantine_event (
  quarantine_id UUID PRIMARY KEY,
  service_name TEXT NOT NULL,
  source_topic TEXT NOT NULL,
  source_partition INTEGER NOT NULL,
  source_offset BIGINT NOT NULL,
  message_id UUID,
  reason_code TEXT NOT NULL,
  reason_detail TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'quarantined',
  raw_message_text TEXT NOT NULL,
  raw_message_json JSONB,
  raw_payload_json JSONB,
  quarantine_hash TEXT NOT NULL,
  replay_attempt_count INTEGER NOT NULL DEFAULT 0,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  resolution_note TEXT,
  UNIQUE (source_topic, source_partition, source_offset),
  CONSTRAINT chk_normalization_quarantine_status
    CHECK (status IN ('quarantined', 'reingested'))
);

CREATE INDEX IF NOT EXISTS idx_normalization_quarantine_status_seen
  ON normalization_quarantine_event (status, last_seen_at DESC);
