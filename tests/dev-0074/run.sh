#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0074] verifying kafka topic SLO + partition/retention policy contract..."

CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
SCHEMA_SQL="infra/timescaledb/init/023_kafka_topic_policy.sql"
DOC_KAFKA="docs/design/ingestion/02-data-platform/kafka-backbone.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"
DOC_SLO="docs/design/ingestion/03-reliability-risk-ops/observability-and-slo-enforcement.md"

grep -q '"/api/v1/control-panel/ingestion/kafka-topic-policy"' "$CHARTING_APP" || { echo "missing kafka topic policy endpoint"; exit 1; }
grep -q "control_panel_ingestion_kafka_topic_policy" "$CHARTING_APP" || { echo "missing kafka topic policy table/runtime usage"; exit 1; }
grep -q "kafka_topic_policies" "$CHARTING_APP" || { echo "missing kafka topic policies projection"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS control_panel_ingestion_kafka_topic_policy" "$SCHEMA_SQL" || { echo "missing kafka topic policy sql contract"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-topic-policy"' "$CP_ROUTER" || { echo "missing control-panel kafka router pass-through"; exit 1; }
grep -q "submitKafkaTopicPolicy" "$CP_JS" || { echo "missing kafka topic policy submit handler in control-panel js"; exit 1; }
grep -q "kafkaTopicPolicyTable" "$CP_JS" || { echo "missing kafka topic policy rendering in control-panel js"; exit 1; }
grep -q "Kafka Topic SLO + Partition/Retention Policy" "$CP_HTML" || { echo "missing kafka policy section in control-panel html"; exit 1; }
grep -q "Kafka Topic SLO + Right-Sizing Contract (DEV-00074)" "$DOC_KAFKA" || { echo "missing DEV-00074 kafka backbone docs"; exit 1; }
grep -q "DEV-00074 Kafka Topic Policy Ops" "$DOC_CP" || { echo "missing DEV-00074 control-panel lld docs"; exit 1; }
grep -q "DEV-00074 Enforcement Checks" "$DOC_SLO" || { echo "missing DEV-00074 SLO enforcement docs"; exit 1; }

echo "[dev-0074] PASS"
