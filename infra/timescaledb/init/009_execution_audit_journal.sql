CREATE TABLE IF NOT EXISTS execution_order_journal (
  order_id UUID PRIMARY KEY,
  venue TEXT NOT NULL,
  canonical_symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL DEFAULT '1m',
  side TEXT NOT NULL,
  requested_notional DOUBLE PRECISION NOT NULL,
  approved BOOLEAN NOT NULL,
  status TEXT NOT NULL,
  decision_ts TIMESTAMPTZ NOT NULL,
  submitted_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at TIMESTAMPTZ,
  execution_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_execution_order_journal_symbol_ts
  ON execution_order_journal (venue, canonical_symbol, updated_at DESC);

CREATE TABLE IF NOT EXISTS audit_event_log (
  audit_id UUID PRIMARY KEY,
  service_name TEXT NOT NULL,
  event_domain TEXT NOT NULL,
  event_type TEXT NOT NULL,
  correlation_id UUID,
  venue TEXT,
  canonical_symbol TEXT,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_event_log_domain_ts
  ON audit_event_log (event_domain, created_at DESC);
