#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n '/api/v1/control-panel/config' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/config/propose' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/config/approve' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/config/apply' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/config/rollback' services/charting/app.py >/dev/null
rg -n 'control_panel_config_registry|control_panel_config_change_request|control_panel_config_change_history' services/charting/app.py >/dev/null
rg -n 'workspace-config|configMetrics|configTable|changeTable|configHistoryTable|loadConfig|proposeConfigChange|approveConfigChange|applyConfigChange|rollbackConfigChange' services/charting/static/control-panel.html >/dev/null

echo "[dev-00033] checks passed"
