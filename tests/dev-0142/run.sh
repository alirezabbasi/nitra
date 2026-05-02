#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0142] verifying rate-limit governance and adaptive throttling policy contract..."

INGEST_APP="services/market-ingestion/src/main.rs"
CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
DOC_CONNECTOR="docs/design/ingestion/02-data-platform/broker-1-connector.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"

grep -q "RateLimitPolicy" "$INGEST_APP" || { echo "missing adaptive throttling policy type in ingestion runtime"; exit 1; }
grep -q "control_panel_ingestion_rate_limit_policy" "$CHARTING_APP" || { echo "missing rate-limit policy contract table/endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/rate-limit-policy"' "$CP_ROUTER" || { echo "missing router pass-through for rate-limit policy"; exit 1; }
grep -q "submitRateLimitPolicy" "$CP_JS" || { echo "missing rate-limit policy submit handler"; exit 1; }
grep -q "rateLimitPolicyTable" "$CP_HTML" || { echo "missing rate-limit policy table in control-panel html"; exit 1; }
grep -q "Adaptive Rate-Limit Governance Contract (DEV-00142)" "$DOC_CONNECTOR" || { echo "missing DEV-00142 connector docs"; exit 1; }
grep -q "DEV-00070 + DEV-00142 Feed Quality + Throttling Ops" "$DOC_CP" || { echo "missing control-panel lld update for DEV-00070/00142"; exit 1; }

echo "[dev-0142] PASS"
