CREATE TABLE IF NOT EXISTS raw_message_capture (
  capture_id UUID PRIMARY KEY,
  message_id UUID NOT NULL,
  service_name TEXT NOT NULL,
  source_topic TEXT NOT NULL,
  source_partition INTEGER NOT NULL,
  source_offset BIGINT NOT NULL,
  venue TEXT NOT NULL,
  broker_symbol TEXT NOT NULL,
  event_ts_received TIMESTAMPTZ NOT NULL,
  sequence_id TEXT,
  sequence_numeric BIGINT,
  previous_sequence_numeric BIGINT,
  sequence_gap BIGINT,
  sequence_status TEXT NOT NULL,
  raw_message_text TEXT NOT NULL,
  raw_message_json JSONB NOT NULL,
  raw_payload_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_topic, source_partition, source_offset)
);

CREATE INDEX IF NOT EXISTS idx_raw_message_capture_symbol_ts
  ON raw_message_capture (venue, broker_symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_message_capture_sequence_status
  ON raw_message_capture (sequence_status, created_at DESC);
