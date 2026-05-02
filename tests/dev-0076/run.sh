#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0076] verifying kafka schema compatibility CI gate contract..."

CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
SCHEMA_SQL="infra/timescaledb/init/025_kafka_schema_compat_log.sql"
GATE_PY="scripts/kafka/schema_compat_gate.py"
GATE_SH="scripts/kafka/schema_compat_gate.sh"
DOC_KAFKA="docs/design/ingestion/02-data-platform/kafka-backbone.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"

grep -q '"/api/v1/control-panel/ingestion/kafka-schema-compat-check"' "$CHARTING_APP" || { echo "missing kafka schema compat endpoint"; exit 1; }
grep -q "control_panel_ingestion_kafka_schema_compat_log" "$CHARTING_APP" || { echo "missing kafka schema compat runtime table usage"; exit 1; }
grep -q "kafka_schema_compat_recent" "$CHARTING_APP" || { echo "missing kafka schema compat projection"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS control_panel_ingestion_kafka_schema_compat_log" "$SCHEMA_SQL" || { echo "missing kafka schema compat sql contract"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-schema-compat-check"' "$CP_ROUTER" || { echo "missing control-panel kafka schema compat router pass-through"; exit 1; }
grep -q "submitKafkaSchemaCompatCheck" "$CP_JS" || { echo "missing kafka schema compat submit handler in control-panel js"; exit 1; }
grep -q "kafkaSchemaCompatTable" "$CP_JS" || { echo "missing kafka schema compat rendering in control-panel js"; exit 1; }
grep -q "Kafka Schema Compatibility CI Gate" "$CP_HTML" || { echo "missing kafka schema compatibility section in control-panel html"; exit 1; }
grep -q "Schema Compatibility CI Gate Contract (DEV-00076)" "$DOC_KAFKA" || { echo "missing DEV-00076 kafka docs"; exit 1; }
grep -q "DEV-00076 Kafka Schema Gate Ops" "$DOC_CP" || { echo "missing DEV-00076 control-panel lld docs"; exit 1; }
[[ -x "$GATE_SH" ]] || { echo "missing executable schema_compat_gate.sh"; exit 1; }
[[ -f "$GATE_PY" ]] || { echo "missing schema_compat_gate.py"; exit 1; }

"$GATE_SH"

echo "[dev-0076] PASS"
