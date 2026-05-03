#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0078] verifying normalization/replay sequence-order integrity verifier..."

NORM_APP="services/market-normalization/src/main.rs"
SCHEMA_SQL="infra/timescaledb/init/027_normalization_sequence_integrity_event.sql"
DOC_STREAM="docs/design/ingestion/02-data-platform/stream-reliability-contracts.md"

grep -q "ensure_normalization_sequence_integrity_table" "$NORM_APP" || { echo "missing normalization sequence-integrity table ensure"; exit 1; }
grep -q "persist_normalization_sequence_integrity_event" "$NORM_APP" || { echo "missing sequence-integrity persistence"; exit 1; }
grep -q "normalized_order_status" "$NORM_APP" || { echo "missing normalized order status classification"; exit 1; }
grep -q "source sequence anomaly detected" "$NORM_APP" || { echo "missing source-sequence anomaly verdict"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS normalization_sequence_integrity_event" "$SCHEMA_SQL" || { echo "missing normalization_sequence_integrity_event sql contract"; exit 1; }
grep -q "Sequence/Order Integrity Verifier (DEV-00078)" "$DOC_STREAM" || { echo "missing DEV-00078 stream reliability docs"; exit 1; }

echo "[dev-0078] PASS"
