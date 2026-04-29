#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0038] FAIL: $1" >&2
  exit 1
}

echo "[dev-0038] checking feature-service baseline files..."
[[ -f services/feature-service/app.py ]] || fail "missing feature-service app"
[[ -f services/feature-service/Dockerfile ]] || fail "missing feature-service Dockerfile"
[[ -f infra/timescaledb/init/013_feature_snapshot.sql ]] || fail "missing feature snapshot migration"


echo "[dev-0038] checking contract wiring..."
rg -n '^features\.snapshot\.v1,' infra/kafka/topics.csv >/dev/null || fail "missing features.snapshot.v1 topic"
rg -n 'FEATURE_INPUT_TOPIC|FEATURE_OUTPUT_TOPIC|FEATURE_GROUP_ID' docker-compose.yml >/dev/null || fail "missing feature-service env wiring"
rg -n 'CREATE TABLE IF NOT EXISTS feature_snapshot' infra/timescaledb/init/013_feature_snapshot.sql >/dev/null || fail "missing feature_snapshot table"
rg -n 'lineage' services/feature-service/app.py >/dev/null || fail "missing lineage payload contract"


echo "[dev-0038] running feature determinism + pit tests..."
python -m py_compile services/feature-service/app.py
python -m unittest discover -s tests/dev-0038/unit -p 'test_*.py'

echo "[dev-0038] PASS"
