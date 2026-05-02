#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0070] verifying inbound feed quality SLA metrics contract..."

INGEST_APP="services/market-ingestion/src/main.rs"
CHARTING_APP="services/charting/app.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
DOC_CONNECTOR="docs/design/ingestion/02-data-platform/broker-1-connector.md"

grep -q "feed_quality" "$INGEST_APP" || { echo "missing feed_quality health payload contract"; exit 1; }
grep -q "sequence_discontinuity_count" "$INGEST_APP" || { echo "missing sequence discontinuity metric in ingestion runtime"; exit 1; }
grep -q "connector_feed_sla" "$CHARTING_APP" || { echo "missing connector_feed_sla in control-panel ingestion api"; exit 1; }
grep -q "Feed Quality SLA" "$CP_HTML" || { echo "missing feed quality sla section in control-panel html"; exit 1; }
grep -q "feedSlaTable" "$CP_JS" || { echo "missing feedSlaTable rendering in control-panel js"; exit 1; }
grep -q "Inbound Feed Quality SLA Contract (DEV-00070)" "$DOC_CONNECTOR" || { echo "missing DEV-00070 connector docs"; exit 1; }

echo "[dev-0070] PASS"
