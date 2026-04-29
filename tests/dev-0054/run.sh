#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0054] FAIL: $1" >&2
  exit 1
}

echo "[dev-0054] checking liquidity structure layer toggle + overlay runtime..."

rg -n 'id="liquidity-layer-toggle"|Liquidity Layer' services/charting/static/index.html >/dev/null || fail "missing chart liquidity layer checkbox"
rg -n 'buildLiquidityStructureModel|buildLiquidityLayerPayload|syncLiquidityLayer|clearLiquidityLayer' services/charting/static/index.html >/dev/null || fail "missing liquidity structure computation/wiring"
rg -n 'registerOverlay\(\{\s*name: "nitraLiquidityLayer"|name: "nitraLiquidityLayer"' services/charting/static/index.html >/dev/null || fail "missing custom liquidity overlay registration"
rg -n 'liquidityLayerEnabled|liquidityLayerOverlayId' services/charting/static/index.html >/dev/null || fail "missing layer state persistence fields"

echo "[dev-0054] PASS"
