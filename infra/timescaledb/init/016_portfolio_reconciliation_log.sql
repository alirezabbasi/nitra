CREATE TABLE IF NOT EXISTS portfolio_reconciliation_log (
  reconciliation_id UUID PRIMARY KEY,
  account_id TEXT NOT NULL,
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  consistent BOOLEAN NOT NULL,
  reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
  computed_gross_exposure DOUBLE PRECISION NOT NULL,
  computed_net_exposure DOUBLE PRECISION NOT NULL,
  account_gross_exposure DOUBLE PRECISION NOT NULL,
  account_net_exposure DOUBLE PRECISION NOT NULL,
  equity DOUBLE PRECISION NOT NULL,
  event_ts TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_reconciliation_log_ts
  ON portfolio_reconciliation_log (account_id, created_at DESC);
