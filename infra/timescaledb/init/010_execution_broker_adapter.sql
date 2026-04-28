ALTER TABLE execution_order_journal
  ADD COLUMN IF NOT EXISTS broker_order_id TEXT;

ALTER TABLE execution_order_journal
  ADD COLUMN IF NOT EXISTS state_version INT NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS uq_execution_order_journal_broker_order_id
  ON execution_order_journal (broker_order_id)
  WHERE broker_order_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS execution_command_log (
  command_id UUID PRIMARY KEY,
  order_id UUID NOT NULL,
  action TEXT NOT NULL,
  accepted BOOLEAN NOT NULL,
  reason TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_execution_command_log_order_ts
  ON execution_command_log (order_id, created_at DESC);
