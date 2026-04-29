#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0046] FAIL: $1" >&2
  exit 1
}

echo "[dev-0046] checking control-panel backend foundation..."
[[ -f services/control-panel/app/main.py ]] || fail "missing control-panel app main.py"
[[ -f services/control-panel/app/api/routers/health.py ]] || fail "missing control-panel health router"
[[ -f services/control-panel/Dockerfile ]] || fail "missing control-panel Dockerfile"

rg -n 'FastAPI\(title="nitra-control-panel"\)' services/control-panel/app/main.py >/dev/null || fail "missing control-panel app bootstrap"
rg -n 'LEGACY_APP|app\.mount\("", LEGACY_APP\)' services/control-panel/app/main.py >/dev/null || fail "missing legacy compatibility bridge"
rg -n '^  control-panel:' docker-compose.yml >/dev/null || fail "missing control-panel compose service"

python -m py_compile services/control-panel/app/main.py services/control-panel/app/api/routers/health.py

echo "[dev-0046] PASS"
