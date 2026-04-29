CREATE TABLE IF NOT EXISTS signal_score_log (
  signal_id UUID PRIMARY KEY,
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  event_ts TIMESTAMPTZ NOT NULL,
  bucket_start TIMESTAMPTZ NOT NULL,
  side TEXT NOT NULL,
  score DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  notional_requested DOUBLE PRECISION NOT NULL,
  reason_codes JSONB NOT NULL,
  scorer_config_version TEXT NOT NULL,
  scorer_model_version TEXT NOT NULL,
  feature_set_version TEXT NOT NULL,
  feature_refs JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_score_log_symbol_ts
  ON signal_score_log (venue, canonical_symbol, timeframe, event_ts DESC);
