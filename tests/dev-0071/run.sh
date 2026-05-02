#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0071] verifying raw data lake canonical partition/object-key contract..."

NORM_APP="services/market-normalization/src/main.rs"
SCHEMA_SQL="infra/timescaledb/init/020_raw_lake_object_manifest.sql"
CHARTING_APP="services/charting/app.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
DOC_LAKE="docs/design/ingestion/02-data-platform/lakehouse-archive.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"

grep -q "canonical_raw_lake_object_key" "$NORM_APP" || { echo "missing canonical object-key builder"; exit 1; }
grep -q "raw_lake_object_manifest" "$NORM_APP" || { echo "missing raw_lake_object_manifest runtime projection"; exit 1; }
grep -q "format=parquet" "$NORM_APP" || { echo "missing parquet object-key partition format"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS raw_lake_object_manifest" "$SCHEMA_SQL" || { echo "missing raw_lake_object_manifest sql contract"; exit 1; }
grep -q "raw_lake_manifest_recent" "$CHARTING_APP" || { echo "missing raw_lake_manifest_recent in ingestion api"; exit 1; }
grep -q "Raw Lake Object Manifest" "$CP_HTML" || { echo "missing raw lake manifest section in control-panel html"; exit 1; }
grep -q "rawLakeManifestTable" "$CP_JS" || { echo "missing raw lake manifest rendering in control-panel js"; exit 1; }
grep -q "Canonical Parquet Partitioning + Object Key Contract (DEV-00071)" "$DOC_LAKE" || { echo "missing DEV-00071 lakehouse docs"; exit 1; }
grep -q "DEV-00071 Raw Lake Ops" "$DOC_CP" || { echo "missing DEV-00071 control-panel lld update"; exit 1; }

echo "[dev-0071] PASS"
