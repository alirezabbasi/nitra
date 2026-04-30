#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0069] verifying session lifecycle + websocket/session reliability contracts..."

CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
DOC_CONNECTOR="docs/design/ingestion/02-data-platform/broker-1-connector.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"

grep -q "control_panel_ingestion_session_policy" "$CHARTING_APP" || { echo "missing session policy contract"; exit 1; }
grep -q "control_panel_ingestion_ws_policy" "$CHARTING_APP" || { echo "missing websocket policy contract"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/session-policy"' "$CHARTING_APP" || { echo "missing session policy endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/ws-policy"' "$CHARTING_APP" || { echo "missing websocket policy endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/session-policy"' "$CP_ROUTER" || { echo "missing control-panel router pass-through for session policy"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/ws-policy"' "$CP_ROUTER" || { echo "missing control-panel router pass-through for ws policy"; exit 1; }
grep -q "submitSessionPolicy" "$CP_JS" || { echo "missing session policy submit handler"; exit 1; }
grep -q "submitWsPolicy" "$CP_JS" || { echo "missing websocket policy submit handler"; exit 1; }
grep -q "sessionPolicyTable" "$CP_HTML" || { echo "missing session policy table"; exit 1; }
grep -q "wsPolicyTable" "$CP_HTML" || { echo "missing ws policy table"; exit 1; }
grep -q "Session Lifecycle Policy Contract (DEV-00069)" "$DOC_CONNECTOR" || { echo "missing DEV-00069 connector docs"; exit 1; }
grep -q "WebSocket/Session Runtime Contract (DEV-00141)" "$DOC_CONNECTOR" || { echo "missing DEV-00141 connector docs"; exit 1; }
grep -q "DEV-00069 + DEV-00141 Feeds Reliability Ops" "$DOC_CP" || { echo "missing control-panel reliability ops docs"; exit 1; }

echo "[dev-0069] PASS"
