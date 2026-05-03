#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0077] verifying normalization/replay deterministic quarantine contract..."

NORM_APP="services/market-normalization/src/main.rs"
NORM_CARGO="services/market-normalization/Cargo.toml"
SCHEMA_SQL="infra/timescaledb/init/026_normalization_quarantine_event.sql"
DOC_STREAM="docs/design/ingestion/02-data-platform/stream-reliability-contracts.md"
DOC_ENV="docs/design/ingestion/07-devdocs/01-development-environment/ingestion-service-env.md"

grep -q "ensure_normalization_quarantine_table" "$NORM_APP" || { echo "missing normalization quarantine table ensure"; exit 1; }
grep -q "persist_quarantine_event" "$NORM_APP" || { echo "missing quarantine persistence handler"; exit 1; }
grep -q "validate_raw_event" "$NORM_APP" || { echo "missing deterministic malformed-event validator"; exit 1; }
grep -q "resolve_quarantine_event_if_reingest" "$NORM_APP" || { echo "missing replay-safe reingest resolution flow"; exit 1; }
grep -q "invalid_envelope_json" "$NORM_APP" || { echo "missing envelope parse quarantine reason"; exit 1; }
grep -q "malformed_market_payload" "$NORM_APP" || { echo "missing malformed payload quarantine reason"; exit 1; }
grep -q "CREATE TABLE IF NOT EXISTS normalization_quarantine_event" "$SCHEMA_SQL" || { echo "missing normalization_quarantine_event sql contract"; exit 1; }
grep -q "md5" "$NORM_CARGO" || { echo "missing deterministic quarantine hash dependency"; exit 1; }
grep -q "Deterministic Quarantine Pipeline (DEV-00077)" "$DOC_STREAM" || { echo "missing DEV-00077 stream reliability docs"; exit 1; }
grep -q "quarantine_reingest" "$DOC_ENV" || { echo "missing reingest header contract docs"; exit 1; }

echo "[dev-0077] PASS"
