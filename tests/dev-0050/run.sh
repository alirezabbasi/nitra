#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0050] FAIL: $1" >&2
  exit 1
}

echo "[dev-0050] running control-panel refactor quality gates..."

# Compatibility contract checks from prior slices.
tests/dev-0049/run.sh

# Backend lint/typecheck-equivalent baseline (deterministic, toolchain-free).
python -m py_compile services/control-panel/app/main.py services/control-panel/app/api/routers/*.py services/control-panel/app/services/control_panel/*.py services/control-panel/app/services/charting/*.py services/control-panel/app/core/*.py

# Router layer hygiene: SQL must stay out of transport handlers.
if rg -n 'SELECT |INSERT |UPDATE |DELETE |FROM ' services/control-panel/app/api/routers/*.py >/dev/null; then
  fail "router files contain inline SQL"
fi

# Frontend build reproducibility and dist parity.
scripts/frontend/build_control_panel_frontend.sh >/dev/null
cmp -s services/control-panel/frontend/src/control-panel.html services/control-panel/frontend/dist/control-panel.html || fail "dist html drift from src"
cmp -s services/control-panel/frontend/src/styles/control-panel.css services/control-panel/frontend/dist/styles/control-panel.css || fail "dist css drift from src"
cmp -s services/control-panel/frontend/src/app/control-panel.js services/control-panel/frontend/dist/app/control-panel.js || fail "dist js drift from src"

# Route availability smoke for backend/frontend/compat endpoints.
tests/dev-0050/smoke_control_panel_routes.sh

echo "[dev-0050] PASS"
