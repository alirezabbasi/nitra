#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0049] FAIL: $1" >&2
  exit 1
}

echo "[dev-0049] checking control-panel frontend app-shell restructure..."

for d in \
  services/control-panel/frontend/src/app \
  services/control-panel/frontend/src/modules \
  services/control-panel/frontend/src/components \
  services/control-panel/frontend/src/services \
  services/control-panel/frontend/src/state \
  services/control-panel/frontend/src/styles; do
  [[ -d "$d" ]] || fail "missing frontend directory: $d"
done

[[ -f services/control-panel/frontend/src/control-panel.html ]] || fail "missing frontend source html"
[[ -f services/control-panel/frontend/src/styles/control-panel.css ]] || fail "missing extracted stylesheet"
[[ -f services/control-panel/frontend/src/app/control-panel.js ]] || fail "missing extracted app shell js"

if rg -n '<style>|<script>' services/control-panel/frontend/src/control-panel.html >/dev/null; then
  fail "control-panel html still contains inline style/script"
fi
rg -n '/control-panel-assets/styles/control-panel.css|/control-panel-assets/app/control-panel.js' services/control-panel/frontend/src/control-panel.html >/dev/null || fail "missing external asset references"
rg -n 'import \{ authedFetch \}|import \{ DENSITY_KEY, SECTION_KEY, TOKEN_KEY \}|import \{ fmt, tableSlice \}' services/control-panel/frontend/src/app/control-panel.js >/dev/null || fail "app shell missing modular imports"
rg -n 'window\.openChartWorkbench|window\.submitAlertAction|window\.switchSection|window\.closePalette' services/control-panel/frontend/src/app/control-panel.js >/dev/null || fail "compatibility globals not exported"

rg -n '"/control-panel-assets"' services/control-panel/app/main.py >/dev/null || fail "control-panel assets mount missing"
rg -n '@app\.get\("/control-panel"\)' services/control-panel/app/main.py >/dev/null || fail "control-panel route missing"

scripts/frontend/build_control_panel_frontend.sh >/dev/null
[[ -f services/control-panel/frontend/dist/control-panel.html ]] || fail "dist html missing"
[[ -f services/control-panel/frontend/dist/styles/control-panel.css ]] || fail "dist css missing"
[[ -f services/control-panel/frontend/dist/app/control-panel.js ]] || fail "dist js missing"

python -m py_compile services/control-panel/app/main.py

echo "[dev-0049] PASS"
