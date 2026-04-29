#!/usr/bin/env bash
set -euo pipefail

[[ -f services/charting/app.py ]]
[[ -f services/charting/static/control-panel.html ]]

python -B -c "import ast, pathlib; ast.parse(pathlib.Path('services/charting/app.py').read_text())"

rg -n '/api/v1/control-panel/search' services/charting/app.py >/dev/null
rg -n 'skip-link|focus-visible|workspace-config|paletteModal|paletteInput|paletteResults|densityBtn|SECTION_KEY|DENSITY_KEY|tableSlice|openPalette|closePalette|searchPalette|Ctrl/Cmd \+ K' services/charting/static/control-panel.html >/dev/null
rg -n 'localStorage\.setItem\(SECTION_KEY|localStorage\.getItem\(SECTION_KEY|applyDensity\(\)' services/charting/static/control-panel.html >/dev/null

echo "[dev-00034] checks passed"
