CREATE TABLE IF NOT EXISTS normalization_sequence_integrity_event (
  integrity_id UUID PRIMARY KEY,
  service_name TEXT NOT NULL,
  source_topic TEXT NOT NULL,
  source_partition INTEGER NOT NULL,
  source_offset BIGINT NOT NULL,
  message_id UUID NOT NULL,
  venue TEXT NOT NULL,
  broker_symbol TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  source_sequence_id TEXT,
  source_sequence_numeric BIGINT,
  source_sequence_status TEXT NOT NULL,
  source_sequence_gap BIGINT,
  normalized_event_ts_received TIMESTAMPTZ NOT NULL,
  previous_normalized_event_ts_received TIMESTAMPTZ,
  normalized_order_status TEXT NOT NULL,
  integrity_status TEXT NOT NULL,
  integrity_reason TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_topic, source_partition, source_offset)
);

CREATE INDEX IF NOT EXISTS idx_norm_seq_integrity_symbol_seen
  ON normalization_sequence_integrity_event (venue, broker_symbol, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_norm_seq_integrity_status_seen
  ON normalization_sequence_integrity_event (integrity_status, observed_at DESC);
