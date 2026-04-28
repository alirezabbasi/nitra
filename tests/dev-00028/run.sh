#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n '/api/v1/control-panel/risk-portfolio' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/risk-limits' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/risk/kill-switch' services/charting/app.py >/dev/null
rg -n 'control_panel_risk_limits' services/charting/app.py >/dev/null
rg -n 'require_min_role\(session\["role"\], "risk_manager"\)' services/charting/app.py >/dev/null
rg -n 'workspace-risk|riskMetrics|strategyTable|riskLimitsBtn|killSwitchBtn|loadRiskPortfolio' services/charting/static/control-panel.html >/dev/null

echo "[dev-00028] checks passed"
