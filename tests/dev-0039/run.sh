#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0039] FAIL: $1" >&2
  exit 1
}

echo "[dev-0039] checking signal-engine baseline files..."
[[ -f services/inference-gateway/app.py ]] || fail "missing signal engine app"
[[ -f infra/timescaledb/init/014_signal_score_log.sql ]] || fail "missing signal score migration"

echo "[dev-0039] checking wiring and contracts..."
rg -n 'SIGNAL_INPUT_TOPIC|SIGNAL_OUTPUT_TOPIC|SIGNAL_GROUP_ID' docker-compose.yml >/dev/null || fail "missing signal env wiring"
rg -n '^decision\.signal_scored\.v1,' infra/kafka/topics.csv >/dev/null || fail "missing decision.signal_scored.v1 topic"
rg -n 'RISK_INPUT_TOPIC: .*decision\.signal_scored\.v1' docker-compose.yml >/dev/null || fail "risk input not wired to signal output"
rg -n 'reason_codes|feature_refs|config_version|model_version' services/inference-gateway/app.py >/dev/null || fail "missing explainability/version contract"

echo "[dev-0039] running scorer tests..."
python -m py_compile services/inference-gateway/app.py
python -m unittest discover -s tests/dev-0039/unit -p 'test_*.py'

echo "[dev-0039] PASS"
