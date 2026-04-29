#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[dev-0055] FAIL: $1" >&2
  exit 1
}

echo "[dev-0055] checking canonical liquidity ontology and chart legend wiring..."

[[ -f docs/design/ontology/liquidity-driven-market-structure-ontology.md ]] || fail "missing ontology markdown"
rg -n 'Core Market Principles|Directional Bias|Pullback Mechanics|Minor Structure|Major Structure|Fractal Observation Contract' docs/design/ontology/liquidity-driven-market-structure-ontology.md >/dev/null || fail "ontology missing required sections"

rg -n 'liquidity-driven-market-structure-ontology\.md' docs/design/nitra_system_hld.md docs/design/nitra_system_lld/10_interpretation_governance_artifacts.md >/dev/null || fail "missing ontology references in HLD/LLD"

rg -n 'id="liquidity-layer-legend"|liquidityLayerSummaryEl|Liquidity Structure Ontology Layer' services/charting/static/index.html >/dev/null || fail "missing chart legend clarity for liquidity layer"

echo "[dev-0055] PASS"
