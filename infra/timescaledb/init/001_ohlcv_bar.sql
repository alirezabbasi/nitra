CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS ohlcv_bar (
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  bucket_start TIMESTAMPTZ NOT NULL,
  open DOUBLE PRECISION NOT NULL,
  high DOUBLE PRECISION NOT NULL,
  low DOUBLE PRECISION NOT NULL,
  close DOUBLE PRECISION NOT NULL,
  volume DOUBLE PRECISION,
  trade_count BIGINT,
  last_event_ts TIMESTAMPTZ NOT NULL,
  inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (venue, canonical_symbol, timeframe, bucket_start)
);

SELECT create_hypertable(
  'ohlcv_bar',
  'bucket_start',
  if_not_exists => TRUE,
  chunk_time_interval => INTERVAL '1 day'
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_bar_symbol_ts
  ON ohlcv_bar (canonical_symbol, bucket_start DESC);

CREATE INDEX IF NOT EXISTS idx_ohlcv_bar_venue_ts
  ON ohlcv_bar (venue, bucket_start DESC);
