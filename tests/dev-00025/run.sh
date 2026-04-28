#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n '@app.get\("/control-panel"\)' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/overview' services/charting/app.py >/dev/null
rg -n 'Operations Overview' services/charting/static/control-panel.html >/dev/null
rg -n 'Full Chart' services/charting/static/control-panel.html >/dev/null
rg -n 'Core Operations|Charting Workbench' services/charting/static/control-panel.html >/dev/null

echo "[dev-00025] checks passed"
