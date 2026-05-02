#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0126] verifying control-panel kafka module contract..."

CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"
DOC_KAFKA="docs/design/ingestion/02-data-platform/kafka-backbone.md"
DOC_STREAM="docs/design/ingestion/02-data-platform/stream-reliability-contracts.md"

grep -q "kafka_topic_policies" "$CHARTING_APP" || { echo "missing kafka topic policy projection"; exit 1; }
grep -q "kafka_lag_recovery_recent" "$CHARTING_APP" || { echo "missing kafka lag recovery projection"; exit 1; }
grep -q "kafka_dead_letter_replay_recent" "$CHARTING_APP" || { echo "missing kafka dead-letter replay projection"; exit 1; }
grep -q "kafka_schema_compat_recent" "$CHARTING_APP" || { echo "missing kafka schema compat projection"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-topic-policy"' "$CHARTING_APP" || { echo "missing kafka topic policy endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-lag-recovery"' "$CHARTING_APP" || { echo "missing kafka lag recovery endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-dead-letter-replay"' "$CHARTING_APP" || { echo "missing kafka dead-letter replay endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-schema-compat-check"' "$CHARTING_APP" || { echo "missing kafka schema compat endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-topic-policy"' "$CP_ROUTER" || { echo "missing kafka topic policy router pass-through"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-lag-recovery"' "$CP_ROUTER" || { echo "missing kafka lag recovery router pass-through"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-dead-letter-replay"' "$CP_ROUTER" || { echo "missing kafka dead-letter replay router pass-through"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-schema-compat-check"' "$CP_ROUTER" || { echo "missing kafka schema compat router pass-through"; exit 1; }
grep -q "kafkaTopicPolicyTable" "$CP_JS" || { echo "missing kafka topic policy render contract in js"; exit 1; }
grep -q "kafkaLagRecoveryTable" "$CP_JS" || { echo "missing lag recovery render contract in js"; exit 1; }
grep -q "kafkaDeadLetterReplayTable" "$CP_JS" || { echo "missing dead-letter replay render contract in js"; exit 1; }
grep -q "kafkaSchemaCompatTable" "$CP_JS" || { echo "missing schema compat render contract in js"; exit 1; }
grep -q "submitKafkaTopicPolicy" "$CP_JS" || { echo "missing kafka topic policy handler"; exit 1; }
grep -q "submitKafkaLagRecovery" "$CP_JS" || { echo "missing lag recovery handler"; exit 1; }
grep -q "submitKafkaDeadLetterReplay" "$CP_JS" || { echo "missing dead-letter replay handler"; exit 1; }
grep -q "submitKafkaSchemaCompatCheck" "$CP_JS" || { echo "missing schema compat handler"; exit 1; }
grep -q "Kafka Topic SLO + Partition/Retention Policy" "$CP_HTML" || { echo "missing kafka topic policy section in html"; exit 1; }
grep -q "Kafka Lag Recovery Automation" "$CP_HTML" || { echo "missing lag recovery section in html"; exit 1; }
grep -q "Kafka Dead-Letter Replay" "$CP_HTML" || { echo "missing dead-letter replay section in html"; exit 1; }
grep -q "Kafka Schema Compatibility CI Gate" "$CP_HTML" || { echo "missing schema compat section in html"; exit 1; }
grep -q "DEV-00126 Kafka Module Consolidation" "$DOC_CP" || { echo "missing DEV-00126 control-panel LLD consolidation docs"; exit 1; }
grep -q "Control-Panel Kafka Module Consolidation (DEV-00126)" "$DOC_KAFKA" || { echo "missing DEV-00126 kafka backbone consolidation docs"; exit 1; }
grep -q "Control-Panel Kafka Module Companion (DEV-00126)" "$DOC_STREAM" || { echo "missing DEV-00126 stream reliability consolidation docs"; exit 1; }

echo "[dev-0126] PASS"
