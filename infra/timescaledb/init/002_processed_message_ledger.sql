CREATE TABLE IF NOT EXISTS processed_message_ledger (
  service_name TEXT NOT NULL,
  message_id UUID NOT NULL,
  source_topic TEXT NOT NULL,
  source_partition INT NOT NULL,
  source_offset BIGINT NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (service_name, message_id),
  UNIQUE (service_name, source_topic, source_partition, source_offset)
);

CREATE INDEX IF NOT EXISTS idx_processed_message_ledger_service_time
  ON processed_message_ledger (service_name, processed_at DESC);
