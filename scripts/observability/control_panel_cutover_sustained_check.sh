#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPORT_DIR="$ROOT_DIR/docs/development/debugging/reports"
mkdir -p "$REPORT_DIR"

BASE_URL="${BASE_URL:-http://localhost:${CHARTING_PORT:-8080}}"
DURATION_SECS="${DURATION_SECS:-180}"
SLEEP_SECS="${SLEEP_SECS:-0.2}"
TIMEOUT_SECS="${TIMEOUT_SECS:-5}"
OUTPUT_PATH="${OUTPUT_PATH:-$REPORT_DIR/control-panel-observability-revalidation-$(date +%Y-%m-%d).md}"
CONTROL_PANEL_TOKEN="${CONTROL_PANEL_TOKEN:-}"

ENDPOINTS=(
  "/control-panel"
  "/api/v1/config"
  "/api/v1/control-panel/migration/status"
  "/api/v1/control-panel/overview"
  "/api/v1/charting/markets/available"
)

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

start_ts="$(date +%s)"
end_ts="$((start_ts + DURATION_SECS))"

while [ "$(date +%s)" -lt "$end_ts" ]; do
  for ep in "${ENDPOINTS[@]}"; do
    curl_args=(-sS -o /dev/null -w "%{http_code} %{time_total}" --connect-timeout "$TIMEOUT_SECS" --max-time "$TIMEOUT_SECS")
    if [ -n "$CONTROL_PANEL_TOKEN" ]; then
      curl_args+=(-H "x-control-panel-token: $CONTROL_PANEL_TOKEN")
    fi
    out="$(curl "${curl_args[@]}" "$BASE_URL$ep" || true)"
    status="${out%% *}"
    latency="${out##* }"
    if [[ "$status" =~ ^[0-9]{3}$ ]] && [[ "$latency" =~ ^[0-9.]+$ ]]; then
      printf "%s\t%s\t%s\n" "$ep" "$status" "$latency" >> "$tmp_file"
    else
      printf "%s\t000\t9.999\n" "$ep" >> "$tmp_file"
    fi
  done
  sleep "$SLEEP_SECS"
done

{
  echo "# Control-Panel Post-Cutover Observability Revalidation"
  echo
  echo "- Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- Base URL: $BASE_URL"
  echo "- Duration seconds: $DURATION_SECS"
  echo "- Sample sleep seconds: $SLEEP_SECS"
  if [ -n "$CONTROL_PANEL_TOKEN" ]; then
    echo "- Auth mode: token header enabled"
  else
    echo "- Auth mode: no token header"
  fi
  echo
  echo "## Thresholds"
  echo
  echo "- HTTP success ratio (2xx/3xx): >= 99.0%"
  echo "- 5xx ratio: <= 0.5%"
  echo "- p95 latency thresholds:"
  echo "  - /control-panel, /api/v1/config, /api/v1/control-panel/migration/status, /api/v1/control-panel/overview: <= 0.75s"
  echo "  - /api/v1/charting/markets/available: <= 2.00s"
  echo
  echo "## Results"
  echo
  echo "| Endpoint | Requests | Success % | 5xx % | p95 latency (s) |"
  echo "|---|---:|---:|---:|---:|"

  awk -F '\t' '
    {
      ep=$1; code=$2+0; lat=$3+0.0;
      n[ep]++;
      if (code>=200 && code<400) ok[ep]++;
      if (code>=500) e5[ep]++;
      latencies[ep, n[ep]] = lat;
    }
    END {
      for (ep in n) {
        count=n[ep];
        success=(count>0 ? (100.0*ok[ep]/count) : 0.0);
        err5=(count>0 ? (100.0*e5[ep]/count) : 0.0);

        # naive insertion sort per endpoint for p95, bounded sample size in this script
        for (i=1; i<=count; i++) arr[i]=latencies[ep,i];
        for (i=2; i<=count; i++) {
          v=arr[i]; j=i-1;
          while (j>=1 && arr[j]>v) { arr[j+1]=arr[j]; j--; }
          arr[j+1]=v;
        }
        idx=int((count*95 + 99)/100); if (idx<1) idx=1; if (idx>count) idx=count;
        p95=arr[idx];

        printf "| %s | %d | %.2f | %.2f | %.3f |\n", ep, count, success, err5, p95;

        delete arr;
      }
    }
  ' "$tmp_file"

  echo
  echo "## Notes"
  echo
  echo "- If any endpoint exceeds thresholds, keep rollout in hold state and investigate before promoting."
  echo "- Attach this file to session evidence and update CURRENT_STATE/WHERE_ARE_WE with outcome."
} > "$OUTPUT_PATH"

echo "[dev-0063] report written: $OUTPUT_PATH"
