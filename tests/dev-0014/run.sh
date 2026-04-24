#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f docs/development/tickets/DEV-00014-venue-history-adapters-and-session-aware-continuity.md ]]

python - <<'PY'
import ast
from pathlib import Path

app = Path("services/charting/app.py")
ast.parse(app.read_text())
print("python syntax ok")
PY

rg -n 'def fetch_capital_range' services/charting/app.py >/dev/null
rg -n 'def capital_session_headers' services/charting/app.py >/dev/null
rg -n 'COINBASE_PUBLIC_REST_URL' services/charting/app.py >/dev/null
rg -n 'continuity_policy' services/charting/app.py >/dev/null
rg -n 'fx_weekday_only_policy' services/charting/app.py >/dev/null
rg -n '/api/v1/backfill/adapter-check' services/charting/app.py >/dev/null
rg -n 'def parse_float' services/charting/app.py >/dev/null

echo "[dev-0014] checks passed"
