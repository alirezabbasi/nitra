CREATE TABLE IF NOT EXISTS coverage_state (
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  last_bucket_start TIMESTAMPTZ NOT NULL,
  last_seen_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (venue, canonical_symbol, timeframe)
);

CREATE TABLE IF NOT EXISTS gap_log (
  gap_id UUID PRIMARY KEY,
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  gap_start TIMESTAMPTZ NOT NULL,
  gap_end TIMESTAMPTZ NOT NULL,
  detected_at TIMESTAMPTZ NOT NULL,
  resolved_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'open',
  source TEXT NOT NULL,
  reason TEXT,
  last_observed_bucket TIMESTAMPTZ,
  new_observed_bucket TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (venue, canonical_symbol, timeframe, gap_start, gap_end)
);

CREATE INDEX IF NOT EXISTS idx_gap_log_open ON gap_log (status, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_gap_log_symbol ON gap_log (venue, canonical_symbol, timeframe, detected_at DESC);

CREATE TABLE IF NOT EXISTS backfill_jobs (
  job_id UUID PRIMARY KEY,
  gap_id UUID,
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  range_start TIMESTAMPTZ NOT NULL,
  range_end TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  attempt_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_backfill_jobs_status ON backfill_jobs (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backfill_jobs_symbol ON backfill_jobs (venue, canonical_symbol, timeframe, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_backfill_jobs_range
  ON backfill_jobs (venue, canonical_symbol, timeframe, range_start, range_end);

CREATE TABLE IF NOT EXISTS replay_audit (
  replay_id UUID PRIMARY KEY,
  source_topic TEXT NOT NULL,
  target_consumer_group TEXT NOT NULL,
  range_start TIMESTAMPTZ,
  range_end TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'queued',
  moved_messages BIGINT NOT NULL DEFAULT 0,
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_replay_audit_status ON replay_audit (status, started_at DESC);
