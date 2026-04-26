CREATE TABLE IF NOT EXISTS risk_state (
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  current_exposure_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
  equity DOUBLE PRECISION NOT NULL DEFAULT 100000,
  drawdown_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
  kill_switch_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  last_decision_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (venue, canonical_symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_risk_state_updated
  ON risk_state (updated_at DESC);

CREATE TABLE IF NOT EXISTS risk_decision_log (
  decision_id UUID PRIMARY KEY,
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  input_topic TEXT NOT NULL,
  side TEXT NOT NULL,
  requested_notional DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  approved BOOLEAN NOT NULL,
  reason TEXT NOT NULL,
  violations JSONB NOT NULL DEFAULT '[]'::jsonb,
  event_ts TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_risk_decision_log_symbol_ts
  ON risk_decision_log (venue, canonical_symbol, created_at DESC);
