CREATE TABLE IF NOT EXISTS incident_evidence_bundle (
  bundle_id UUID PRIMARY KEY,
  exported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  taxonomy_version TEXT NOT NULL,
  correlation_id UUID NOT NULL,
  order_id UUID NOT NULL,
  venue TEXT,
  canonical_symbol TEXT,
  lineage JSONB NOT NULL DEFAULT '{}'::jsonb,
  artifacts JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_incident_evidence_bundle_corr_ts
  ON incident_evidence_bundle (correlation_id, exported_at DESC);

CREATE INDEX IF NOT EXISTS idx_incident_evidence_bundle_order_ts
  ON incident_evidence_bundle (order_id, exported_at DESC);
