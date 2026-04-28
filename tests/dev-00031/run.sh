#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n '/api/v1/control-panel/ops' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/ops/alerts/action' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/ops/alerts/ingest' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/ops/runbook/execute' services/charting/app.py >/dev/null
rg -n 'control_panel_alert|control_panel_incident|control_panel_runbook_execution' services/charting/app.py >/dev/null
rg -n 'workspace-ops|opsMetrics|alertTable|incidentTable|runbookTable|submitRunbook|submitAlertAction|submitOpsAlert|loadOps' services/charting/static/control-panel.html >/dev/null


echo "[dev-00031] checks passed"
