#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n '/api/v1/control-panel/execution' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/execution/command' services/charting/app.py >/dev/null
rg -n 'execution_order_journal|execution_command_log|audit_event_log' services/charting/app.py >/dev/null
rg -n 'require_min_role\(session\["role"\], "operator"\)' services/charting/app.py >/dev/null
rg -n 'workspace-execution|executionMetrics|ordersTable|commandsTable|reconciliationTable|brokerDiagTable|submitExecutionCommand|loadExecution' services/charting/static/control-panel.html >/dev/null

echo "[dev-00029] checks passed"
