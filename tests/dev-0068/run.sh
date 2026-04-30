#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0068] verifying failover policy contract + control-panel controls..."

CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
DOC_CONNECTOR="docs/design/ingestion/02-data-platform/broker-1-connector.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"

grep -q "control_panel_ingestion_failover_policy" "$CHARTING_APP" || { echo "missing charting failover endpoint"; exit 1; }
grep -q "control_panel_ingestion_failover_policy_table" "$CHARTING_APP" || { echo "missing failover policy table contract"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/failover-policy"' "$CP_ROUTER" || { echo "missing control-panel ingestion router pass-through"; exit 1; }
grep -q "submitFailoverPolicy" "$CP_JS" || { echo "missing failover submit handler in control-panel js"; exit 1; }
grep -q "failoverPolicyTable" "$CP_HTML" || { echo "missing failover policy table in control-panel html"; exit 1; }
grep -q "Failover Policy Contract (DEV-00068)" "$DOC_CONNECTOR" || { echo "missing connector failover contract docs"; exit 1; }
grep -q "DEV-00124 Feeds Ops Snapshot" "$DOC_CP" || { echo "missing control-panel feeds ops docs"; exit 1; }

echo "[dev-0068] PASS"
