#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0143] verifying raw message capture conformance contract..."

NORM_APP="services/market-normalization/src/main.rs"
SCHEMA_SQL="infra/timescaledb/init/019_raw_message_capture.sql"
CHARTING_APP="services/charting/app.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
DOC_CONNECTOR="docs/design/ingestion/02-data-platform/broker-1-connector.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"

grep -q "raw_message_capture" "$NORM_APP" || { echo "missing raw_message_capture runtime persistence"; exit 1; }
grep -q "raw_message_text" "$NORM_APP" || { echo "missing untouched raw_message_text persistence"; exit 1; }
grep -q "sequence_status" "$NORM_APP" || { echo "missing sequence provenance status logic"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS raw_message_capture" "$SCHEMA_SQL" || { echo "missing raw_message_capture sql contract"; exit 1; }
grep -q "raw_capture_recent" "$CHARTING_APP" || { echo "missing raw_capture_recent in control-panel ingestion api"; exit 1; }
grep -q "Raw Capture Provenance" "$CP_HTML" || { echo "missing raw capture provenance section in control-panel html"; exit 1; }
grep -q "rawCaptureTable" "$CP_JS" || { echo "missing raw capture rendering in control-panel js"; exit 1; }
grep -q "Raw Message Capture Conformance Contract (DEV-00143)" "$DOC_CONNECTOR" || { echo "missing DEV-00143 connector docs"; exit 1; }
grep -q "DEV-00143 Raw Capture Ops" "$DOC_CP" || { echo "missing DEV-00143 control-panel lld update"; exit 1; }

echo "[dev-0143] PASS"
