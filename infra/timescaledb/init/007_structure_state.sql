CREATE TABLE IF NOT EXISTS structure_state (
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  trend TEXT NOT NULL DEFAULT 'neutral',
  phase TEXT NOT NULL DEFAULT 'init',
  objective TEXT NOT NULL DEFAULT 'none',
  swing_high DOUBLE PRECISION NOT NULL,
  swing_low DOUBLE PRECISION NOT NULL,
  last_bucket_start TIMESTAMPTZ NOT NULL,
  last_close DOUBLE PRECISION NOT NULL,
  extension_count INT NOT NULL DEFAULT 0,
  pullback_count INT NOT NULL DEFAULT 0,
  inside_bars INT NOT NULL DEFAULT 0,
  outside_bars INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (venue, canonical_symbol, timeframe)
);

CREATE INDEX IF NOT EXISTS idx_structure_state_updated
  ON structure_state (updated_at DESC);
