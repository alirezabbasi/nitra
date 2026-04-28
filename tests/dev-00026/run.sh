#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n 'ROLE_RANK' services/charting/app.py >/dev/null
rg -n 'get_operator_session' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/session' services/charting/app.py >/dev/null
rg -n '/api/v1/control-panel/actions/privileged' services/charting/app.py >/dev/null
rg -n 'control_panel_audit_log' services/charting/app.py >/dev/null
rg -n 'X-Control-Panel-Token' services/charting/static/control-panel.html >/dev/null
rg -n 'sessionPill|applyRoleVisibility|TOKEN_KEY' services/charting/static/control-panel.html >/dev/null

echo "[dev-00026] checks passed"
