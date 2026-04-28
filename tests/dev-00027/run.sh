#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n '/api/v1/control-panel/ingestion' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/ingestion/backfill-window' services/charting/app.py >/dev/null
rg -n 'require_min_role\(session\["role"\], "operator"\)' services/charting/app.py >/dev/null
rg -n 'window exceeds 7 days safety cap' services/charting/app.py >/dev/null
rg -n 'ingestionMetrics|connectorTable|backfillTable|replayTable|submitBackfillWindow|loadIngestion' services/charting/static/control-panel.html >/dev/null

echo "[dev-00027] checks passed"
