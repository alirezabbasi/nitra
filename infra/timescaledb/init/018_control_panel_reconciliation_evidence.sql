CREATE TABLE IF NOT EXISTS control_panel_reconciliation_evidence (
  evidence_id UUID PRIMARY KEY,
  execution_id UUID REFERENCES control_panel_runbook_execution(execution_id) ON DELETE CASCADE,
  incident_id UUID REFERENCES control_panel_incident(incident_id) ON DELETE SET NULL,
  order_id UUID,
  correlation_id UUID,
  source TEXT NOT NULL,
  evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_control_panel_reconciliation_evidence_execution_ts
  ON control_panel_reconciliation_evidence (execution_id, captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_control_panel_reconciliation_evidence_order_ts
  ON control_panel_reconciliation_evidence (order_id, captured_at DESC);
