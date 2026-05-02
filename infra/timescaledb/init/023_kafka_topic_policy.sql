CREATE TABLE IF NOT EXISTS control_panel_ingestion_kafka_topic_policy (
  topic_name TEXT PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  target_partitions INTEGER NOT NULL DEFAULT 6,
  retention_ms BIGINT NOT NULL DEFAULT -1,
  cleanup_policy TEXT NOT NULL DEFAULT 'delete',
  max_consumer_lag_messages BIGINT NOT NULL DEFAULT 10000,
  max_consumer_lag_seconds INTEGER NOT NULL DEFAULT 60,
  min_insync_replicas INTEGER NOT NULL DEFAULT 1,
  updated_by TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_kafka_topic_partitions
    CHECK (target_partitions >= 1 AND target_partitions <= 96),
  CONSTRAINT chk_kafka_topic_retention
    CHECK (retention_ms = -1 OR (retention_ms >= 60000 AND retention_ms <= 31536000000)),
  CONSTRAINT chk_kafka_cleanup_policy
    CHECK (cleanup_policy IN ('delete', 'compact', 'compact,delete', 'delete,compact')),
  CONSTRAINT chk_kafka_lag_messages
    CHECK (max_consumer_lag_messages >= 1 AND max_consumer_lag_messages <= 100000000),
  CONSTRAINT chk_kafka_lag_seconds
    CHECK (max_consumer_lag_seconds >= 1 AND max_consumer_lag_seconds <= 86400),
  CONSTRAINT chk_kafka_min_isr
    CHECK (min_insync_replicas >= 1 AND min_insync_replicas <= 5)
);
