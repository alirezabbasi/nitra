#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0125] verifying control-panel raw-lake module contract..."

CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"
DOC_LAKE="docs/design/ingestion/02-data-platform/lakehouse-archive.md"

grep -q "raw_lake_manifest_recent" "$CHARTING_APP" || { echo "missing raw_lake_manifest_recent projection"; exit 1; }
grep -q "replay_manifest_recent" "$CHARTING_APP" || { echo "missing replay_manifest_recent projection"; exit 1; }
grep -q "raw_lake_retention_policies" "$CHARTING_APP" || { echo "missing raw_lake_retention_policies projection"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/raw-lake/replay-manifest"' "$CHARTING_APP" || { echo "missing replay manifest endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/raw-lake/retention-policy"' "$CHARTING_APP" || { echo "missing retention policy endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/raw-lake/replay-manifest"' "$CP_ROUTER" || { echo "missing replay manifest router pass-through"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/raw-lake/retention-policy"' "$CP_ROUTER" || { echo "missing retention policy router pass-through"; exit 1; }
grep -q "rawLakeManifestTable" "$CP_JS" || { echo "missing raw lake manifest render contract in js"; exit 1; }
grep -q "buildReplayManifest" "$CP_JS" || { echo "missing replay manifest build handler"; exit 1; }
grep -q "submitRawLakeRetentionPolicy" "$CP_JS" || { echo "missing retention policy handler"; exit 1; }
grep -q "Raw Lake Object Manifest (Recent)" "$CP_HTML" || { echo "missing partition browser section in html"; exit 1; }
grep -q "Replay Manifest Index Builder" "$CP_HTML" || { echo "missing replay manifest section in html"; exit 1; }
grep -q "Raw Lake Retention/Tiering Policy" "$CP_HTML" || { echo "missing retention controls section in html"; exit 1; }
grep -q "DEV-00125 Raw Lake Module Consolidation" "$DOC_CP" || { echo "missing DEV-00125 control-panel LLD consolidation docs"; exit 1; }
grep -q "Control-Panel Raw Lake Module Consolidation (DEV-00125)" "$DOC_LAKE" || { echo "missing DEV-00125 lakehouse consolidation docs"; exit 1; }

echo "[dev-0125] PASS"
