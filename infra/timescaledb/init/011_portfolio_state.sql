CREATE TABLE IF NOT EXISTS portfolio_position_state (
  account_id TEXT NOT NULL,
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  net_position_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
  gross_exposure_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
  last_order_id UUID,
  last_fill_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
  last_fill_side TEXT,
  last_fill_ts TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (account_id, venue, canonical_symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_position_state_updated
  ON portfolio_position_state (updated_at DESC);

CREATE TABLE IF NOT EXISTS portfolio_account_state (
  account_id TEXT PRIMARY KEY,
  equity DOUBLE PRECISION NOT NULL DEFAULT 100000,
  gross_exposure_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
  net_exposure_notional DOUBLE PRECISION NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS portfolio_fill_log (
  fill_id UUID PRIMARY KEY,
  account_id TEXT NOT NULL,
  order_id UUID NOT NULL,
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  side TEXT NOT NULL,
  filled_notional DOUBLE PRECISION NOT NULL,
  event_ts TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_fill_log_symbol_ts
  ON portfolio_fill_log (account_id, venue, canonical_symbol, created_at DESC);
