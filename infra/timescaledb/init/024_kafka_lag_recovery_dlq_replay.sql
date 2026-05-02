CREATE TABLE IF NOT EXISTS control_panel_ingestion_kafka_lag_recovery_log (
  recovery_id UUID PRIMARY KEY,
  topic_name TEXT NOT NULL,
  consumer_group TEXT NOT NULL,
  observed_lag_messages BIGINT NOT NULL,
  observed_lag_seconds BIGINT NOT NULL,
  dlq_topic TEXT NOT NULL,
  replay_from_offset BIGINT,
  replay_to_offset BIGINT,
  status TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_kafka_lag_messages
    CHECK (observed_lag_messages >= 1 AND observed_lag_messages <= 1000000000),
  CONSTRAINT chk_kafka_lag_seconds
    CHECK (observed_lag_seconds >= 1 AND observed_lag_seconds <= 172800),
  CONSTRAINT chk_kafka_lag_dlq_topic
    CHECK (right(dlq_topic, 4) = '.dlq')
);

CREATE TABLE IF NOT EXISTS control_panel_ingestion_kafka_dead_letter_replay_log (
  replay_id UUID PRIMARY KEY,
  source_topic TEXT NOT NULL,
  dlq_topic TEXT NOT NULL,
  target_consumer_group TEXT NOT NULL,
  replay_mode TEXT NOT NULL,
  message_count BIGINT NOT NULL,
  status TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_kafka_dlq_topic
    CHECK (right(dlq_topic, 4) = '.dlq'),
  CONSTRAINT chk_kafka_replay_mode
    CHECK (replay_mode IN ('dry_run', 'execute')),
  CONSTRAINT chk_kafka_replay_messages
    CHECK (message_count >= 1 AND message_count <= 10000000)
);

CREATE INDEX IF NOT EXISTS idx_control_panel_kafka_lag_recovery_created_at
  ON control_panel_ingestion_kafka_lag_recovery_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_control_panel_kafka_dlq_replay_created_at
  ON control_panel_ingestion_kafka_dead_letter_replay_log (created_at DESC);
