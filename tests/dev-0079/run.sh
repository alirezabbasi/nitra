#!/usr/bin/env bash
set -euo pipefail

echo "[dev-0079] verifying 90-day startup coverage conformance harness with venue-session fixtures..."

GAP_APP="services/gap-detection/src/main.rs"
DOC_ENV="docs/design/ingestion/07-devdocs/01-development-environment/ingestion-service-env.md"
DOC_STREAM="docs/design/ingestion/02-data-platform/stream-reliability-contracts.md"

grep -q "FxSessionPolicy" "$GAP_APP" || { echo "missing fx session policy contract"; exit 1; }
grep -q "find_missing_ranges_in_window_with_policy" "$GAP_APP" || { echo "missing policy-aware missing-range harness"; exit 1; }
grep -q "expected_coverage_bucket" "$GAP_APP" || { echo "missing venue-session expected bucket classifier"; exit 1; }
grep -q "fx_weekend_edge_case_is_excluded_from_gap_expectations" "$GAP_APP" || { echo "missing fx weekend fixture"; exit 1; }
grep -q "crypto_weekend_edge_case_is_still_required_coverage" "$GAP_APP" || { echo "missing crypto weekend fixture"; exit 1; }
grep -q "FX_WEEKEND_START_ISO_DOW" "$GAP_APP" || { echo "missing weekend policy env wiring in gap-detection"; exit 1; }
grep -q "run_coverage_scan(" "$GAP_APP" || { echo "missing startup coverage scan harness"; exit 1; }
grep -q "startup_90d_missing" "$GAP_APP" || { echo "missing startup 90d conformance reason"; exit 1; }
grep -q "DEV-00079" "$DOC_STREAM" || { echo "missing DEV-00079 stream reliability docs"; exit 1; }
grep -qi "gap-detection coverage scan also honors FX weekend session policy" "$DOC_ENV" || { echo "missing gap-detection weekend policy env docs"; exit 1; }

cargo test --manifest-path services/gap-detection/Cargo.toml >/dev/null

echo "[dev-0079] PASS"
