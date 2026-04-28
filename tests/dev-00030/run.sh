#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n '/api/v1/control-panel/charting/profile' services/charting/app.py >/dev/null
rg -n 'full_chart|bars_history_api|latest_execution_state|open_gap_count' services/charting/app.py >/dev/null
rg -n 'workspace-charting|cwVenue|cwSymbol|cwTimeframe|cwFrame|openChartWorkbench|loadChartingWorkbench' services/charting/static/control-panel.html >/dev/null
rg -n 'onclick="openChartWorkbench\(' services/charting/static/control-panel.html >/dev/null

echo "[dev-00030] checks passed"
