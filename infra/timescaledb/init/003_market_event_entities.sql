CREATE TABLE IF NOT EXISTS raw_tick (
  message_id UUID NOT NULL,
  venue TEXT NOT NULL,
  broker_symbol TEXT NOT NULL,
  event_ts_exchange TIMESTAMPTZ,
  event_ts_received TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  bid DOUBLE PRECISION,
  ask DOUBLE PRECISION,
  mid DOUBLE PRECISION,
  last DOUBLE PRECISION,
  sequence_id TEXT,
  payload JSONB NOT NULL,
  inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (message_id, event_ts_received)
);

SELECT create_hypertable(
  'raw_tick',
  'event_ts_received',
  if_not_exists => TRUE,
  chunk_time_interval => INTERVAL '1 day'
);

CREATE INDEX IF NOT EXISTS idx_raw_tick_venue_symbol_ts
  ON raw_tick (venue, broker_symbol, event_ts_received DESC);

CREATE INDEX IF NOT EXISTS idx_raw_tick_message_id
  ON raw_tick (message_id);

CREATE TABLE IF NOT EXISTS trade_print (
  message_id UUID NOT NULL,
  venue TEXT NOT NULL,
  broker_symbol TEXT NOT NULL,
  event_ts_exchange TIMESTAMPTZ,
  event_ts_received TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  price DOUBLE PRECISION,
  size DOUBLE PRECISION,
  side TEXT,
  sequence_id TEXT,
  payload JSONB NOT NULL,
  inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (message_id, event_ts_received)
);

SELECT create_hypertable(
  'trade_print',
  'event_ts_received',
  if_not_exists => TRUE,
  chunk_time_interval => INTERVAL '1 day'
);

CREATE INDEX IF NOT EXISTS idx_trade_print_venue_symbol_ts
  ON trade_print (venue, broker_symbol, event_ts_received DESC);

CREATE INDEX IF NOT EXISTS idx_trade_print_message_id
  ON trade_print (message_id);

CREATE TABLE IF NOT EXISTS book_event (
  message_id UUID NOT NULL,
  venue TEXT NOT NULL,
  broker_symbol TEXT NOT NULL,
  event_ts_exchange TIMESTAMPTZ,
  event_ts_received TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  best_bid DOUBLE PRECISION,
  best_ask DOUBLE PRECISION,
  sequence_id TEXT,
  payload JSONB NOT NULL,
  inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (message_id, event_ts_received)
);

SELECT create_hypertable(
  'book_event',
  'event_ts_received',
  if_not_exists => TRUE,
  chunk_time_interval => INTERVAL '1 day'
);

CREATE INDEX IF NOT EXISTS idx_book_event_venue_symbol_ts
  ON book_event (venue, broker_symbol, event_ts_received DESC);

CREATE INDEX IF NOT EXISTS idx_book_event_message_id
  ON book_event (message_id);
