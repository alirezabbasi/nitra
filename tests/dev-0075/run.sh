#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0075] verifying kafka lag recovery + dead-letter replay hardening contract..."

CHARTING_APP="services/charting/app.py"
CP_ROUTER="services/control-panel/app/api/routers/ingestion.py"
CP_JS="services/control-panel/frontend/src/app/control-panel.js"
CP_HTML="services/control-panel/frontend/src/control-panel.html"
SCHEMA_SQL="infra/timescaledb/init/024_kafka_lag_recovery_dlq_replay.sql"
DOC_KAFKA="docs/design/ingestion/02-data-platform/stream-reliability-contracts.md"
DOC_CP="docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md"
DOC_SLO="docs/design/ingestion/03-reliability-risk-ops/observability-and-slo-enforcement.md"

grep -q '"/api/v1/control-panel/ingestion/kafka-lag-recovery"' "$CHARTING_APP" || { echo "missing kafka lag recovery endpoint"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-dead-letter-replay"' "$CHARTING_APP" || { echo "missing kafka dead-letter replay endpoint"; exit 1; }
grep -q "kafka_lag_recovery_recent" "$CHARTING_APP" || { echo "missing kafka lag recovery projection"; exit 1; }
grep -q "kafka_dead_letter_replay_recent" "$CHARTING_APP" || { echo "missing kafka dead-letter replay projection"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS control_panel_ingestion_kafka_lag_recovery_log" "$SCHEMA_SQL" || { echo "missing kafka lag recovery sql contract"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS control_panel_ingestion_kafka_dead_letter_replay_log" "$SCHEMA_SQL" || { echo "missing kafka dead-letter replay sql contract"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-lag-recovery"' "$CP_ROUTER" || { echo "missing control-panel kafka lag recovery router pass-through"; exit 1; }
grep -q '"/api/v1/control-panel/ingestion/kafka-dead-letter-replay"' "$CP_ROUTER" || { echo "missing control-panel kafka dead-letter replay router pass-through"; exit 1; }
grep -q "submitKafkaLagRecovery" "$CP_JS" || { echo "missing kafka lag recovery submit handler in control-panel js"; exit 1; }
grep -q "submitKafkaDeadLetterReplay" "$CP_JS" || { echo "missing kafka dead-letter replay submit handler in control-panel js"; exit 1; }
grep -q "Kafka Lag Recovery Automation" "$CP_HTML" || { echo "missing kafka lag recovery section in control-panel html"; exit 1; }
grep -q "Kafka Dead-Letter Replay" "$CP_HTML" || { echo "missing kafka dead-letter replay section in control-panel html"; exit 1; }
grep -q "DLQ Recovery + Replay Hardening Contract (DEV-00075)" "$DOC_KAFKA" || { echo "missing DEV-00075 stream reliability docs"; exit 1; }
grep -q "DEV-00075 Kafka Recovery Ops" "$DOC_CP" || { echo "missing DEV-00075 control-panel lld docs"; exit 1; }
grep -q "DEV-00075 Lag-Recovery Enforcement" "$DOC_SLO" || { echo "missing DEV-00075 SLO enforcement docs"; exit 1; }

echo "[dev-0075] PASS"
