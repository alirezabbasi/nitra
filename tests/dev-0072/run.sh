#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0072] verifying replay manifest/index service contract..."

CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
SCHEMA_SQL="infra/timescaledb/init/021_raw_lake_replay_manifest_index.sql"
DOC_LAKE="docs/design/ingestion/02-data-platform/lakehouse-archive.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"

grep -q '"/api/v1/control-panel/ingestion/raw-lake/replay-manifest"' "$CHARTING_APP" || { echo "missing replay manifest build endpoint"; exit 1; }
grep -q "raw_lake_replay_manifest_index" "$CHARTING_APP" || { echo "missing replay manifest index table/runtime usage"; exit 1; }
grep -q "checksum_sha256" "$CHARTING_APP" || { echo "missing deterministic manifest checksum field"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS raw_lake_replay_manifest_index" "$SCHEMA_SQL" || { echo "missing replay manifest index sql contract"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/raw-lake/replay-manifest"' "$CP_ROUTER" || { echo "missing control-panel router pass-through"; exit 1; }
grep -q "buildReplayManifest" "$CP_JS" || { echo "missing replay manifest build handler in control-panel js"; exit 1; }
grep -q "Replay Manifest Index Builder" "$CP_HTML" || { echo "missing replay manifest builder section in control-panel html"; exit 1; }
grep -q "Replay Manifest/Index Contract (DEV-00072)" "$DOC_LAKE" || { echo "missing DEV-00072 lakehouse docs"; exit 1; }
grep -q "DEV-00072 Replay Manifest Ops" "$DOC_CP" || { echo "missing DEV-00072 control-panel lld docs"; exit 1; }

echo "[dev-0072] PASS"
