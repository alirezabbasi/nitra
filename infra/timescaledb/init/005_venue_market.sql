CREATE TABLE IF NOT EXISTS venue_market (
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  asset_class TEXT NOT NULL DEFAULT 'fx',
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  ingest_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (venue, symbol),
  CHECK (asset_class IN ('fx', 'crypto', 'other'))
);

CREATE INDEX IF NOT EXISTS idx_venue_market_enabled
  ON venue_market (enabled, ingest_enabled, venue, symbol);

INSERT INTO venue_market (venue, symbol, asset_class, enabled, ingest_enabled)
VALUES
  ('oanda', 'EURUSD', 'fx', TRUE, TRUE),
  ('oanda', 'GBPUSD', 'fx', TRUE, TRUE),
  ('oanda', 'USDJPY', 'fx', TRUE, TRUE),
  ('capital', 'EURUSD', 'fx', TRUE, TRUE),
  ('capital', 'GBPUSD', 'fx', TRUE, TRUE),
  ('coinbase', 'BTCUSD', 'crypto', TRUE, TRUE),
  ('coinbase', 'ETHUSD', 'crypto', TRUE, TRUE),
  ('coinbase', 'SOLUSD', 'crypto', TRUE, TRUE),
  ('coinbase', 'ADAUSD', 'crypto', TRUE, TRUE),
  ('coinbase', 'XRPUSD', 'crypto', TRUE, TRUE),
  ('coinbase', 'EURUSD', 'other', TRUE, FALSE)
ON CONFLICT (venue, symbol) DO NOTHING;
