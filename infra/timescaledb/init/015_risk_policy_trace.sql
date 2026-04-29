ALTER TABLE risk_decision_log
  ADD COLUMN IF NOT EXISTS policy_hits JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE risk_decision_log
  ADD COLUMN IF NOT EXISTS evaluation_trace JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_risk_decision_log_policy_hits
  ON risk_decision_log USING GIN (policy_hits);
