#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0073] verifying raw lake retention/tiering + restore-drill contract..."

CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
SCHEMA_SQL="infra/timescaledb/init/022_raw_lake_retention_restore.sql"
DOC_LAKE="docs/design/ingestion/02-data-platform/lakehouse-archive.md"
DOC_DR="docs/design/ingestion/06-devops/operations-backup-dr.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"

grep -q '"/api/v1/control-panel/ingestion/raw-lake/retention-policy"' "$CHARTING_APP" || { echo "missing retention policy endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/raw-lake/restore-drill"' "$CHARTING_APP" || { echo "missing restore drill endpoint"; exit 1; }
grep -q "raw_lake_retention_policies" "$CHARTING_APP" || { echo "missing retention policy projection in ingestion payload"; exit 1; }
grep -q "raw_lake_restore_drills" "$CHARTING_APP" || { echo "missing restore drill projection in ingestion payload"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS raw_lake_retention_policy" "$SCHEMA_SQL" || { echo "missing raw_lake_retention_policy sql contract"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS raw_lake_restore_validation_log" "$SCHEMA_SQL" || { echo "missing raw_lake_restore_validation_log sql contract"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/raw-lake/retention-policy"' "$CP_ROUTER" || { echo "missing control-panel retention router pass-through"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/raw-lake/restore-drill"' "$CP_ROUTER" || { echo "missing control-panel restore-drill router pass-through"; exit 1; }
grep -q "submitRawLakeRetentionPolicy" "$CP_JS" || { echo "missing retention policy submit handler in control-panel js"; exit 1; }
grep -q "submitRawLakeRestoreDrill" "$CP_JS" || { echo "missing restore drill submit handler in control-panel js"; exit 1; }
grep -q "Raw Lake Retention/Tiering Policy" "$CP_HTML" || { echo "missing retention policy section in control-panel html"; exit 1; }
grep -q "Restore Drill Evidence" "$CP_HTML" || { echo "missing restore drill section in control-panel html"; exit 1; }
grep -q "Retention/Tiering + Restore Validation Contract (DEV-00073)" "$DOC_LAKE" || { echo "missing DEV-00073 lakehouse docs"; exit 1; }
grep -q "DEV-00073 Backup/DR Restore Drill Runbook" "$DOC_DR" || { echo "missing DEV-00073 DR runbook docs"; exit 1; }
grep -q "DEV-00073 Raw Lake Retention Ops" "$DOC_CP" || { echo "missing DEV-00073 control-panel lld docs"; exit 1; }

echo "[dev-0073] PASS"
