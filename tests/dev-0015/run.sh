#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/index.html ]]
[[ -f docs/development/tickets/DEV-00015-chart-interaction-ux-commercial-parity.md ]]

python - <<'PY'
import ast
from pathlib import Path

ast.parse(Path('services/charting/app.py').read_text())
print('python syntax ok')
PY

rg -n '@app.get\("/api/v1/bars/history"\)' services/charting/app.py >/dev/null
rg -n 'def bars_history' services/charting/app.py >/dev/null

rg -n 'realtime-btn|jump-time-btn|jump-index-btn|snapshot-btn' services/charting/static/index.html >/dev/null
rg -n 'zoom-anchor-select|bar-space-range|right-offset-range' services/charting/static/index.html >/dev/null
rg -n 'lock-scroll-btn|lock-zoom-btn|locale-select|timezone-select|format-select' services/charting/static/index.html >/dev/null
rg -n 'scrollToRealTime|scrollToTimestamp|scrollToDataIndex|zoomAtTimestamp' services/charting/static/index.html >/dev/null
rg -n 'setZoomAnchor|setBarSpace|setOffsetRightDistance|setLeftMinVisibleBarCount|setRightMinVisibleBarCount' services/charting/static/index.html >/dev/null
rg -n 'setZoomEnabled|setScrollEnabled|subscribeAction|convertFromPixel|getConvertPictureUrl' services/charting/static/index.html >/dev/null
rg -n 'loadOlderBarsIfNeeded|/api/v1/bars/history' services/charting/static/index.html >/dev/null

echo "[dev-0015] checks passed"
