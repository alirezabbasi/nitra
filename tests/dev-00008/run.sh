#!/usr/bin/env bash
set -euo pipefail

for f in \
  services/charting/app.py \
  services/charting/Dockerfile \
  services/charting/requirements.txt \
  services/charting/static/index.html \
  services/charting/static/vendor-klinecharts.min.js; do
  [[ -f "$f" ]]
done

python -m py_compile services/charting/app.py

rg -n '^  charting:' docker-compose.yml >/dev/null
rg -n -F 'CHARTING_PORT=8110' .env.example >/dev/null
rg -n -F 'CHARTING_PORT}:8080' docker-compose.yml >/dev/null
rg -n -F 'CHARTING_TIMEFRAME' docker-compose.yml >/dev/null
rg -n -F 'CHARTING_DEFAULT_LIMIT' docker-compose.yml >/dev/null
rg -n -F 'CHARTING_REFRESH_SECS' docker-compose.yml >/dev/null
rg -n -F 'klinecharts' services/charting/static/index.html >/dev/null
rg -n -F '/static/vendor-klinecharts.min.js' services/charting/static/index.html >/dev/null
rg -n '/api/v1/markets/available' services/charting/app.py >/dev/null
rg -n '/api/v1/bars/hot' services/charting/app.py >/dev/null
rg -n '/api/v1/ticks/hot' services/charting/app.py >/dev/null

echo "[dev-00008] checks passed"
