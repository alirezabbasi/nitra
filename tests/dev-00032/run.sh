#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n '/api/v1/control-panel/research' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/research/backtest' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/research/model/promote' services/charting/app.py >/dev/null
rg -n 'control_panel_dataset_registry|control_panel_backtest_run|control_panel_model_registry' services/charting/app.py >/dev/null
rg -n 'workspace-research|researchMetrics|datasetTable|backtestTable|modelTable|loadResearch|submitBacktest|submitModelPromotion' services/charting/static/control-panel.html >/dev/null

echo "[dev-00032] checks passed"
