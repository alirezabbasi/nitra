#!/usr/bin/env bash
set -euo pipefail

[[ ! -f services/ingestion/mock_pricing.py ]]

# Guardrail: ingestion runtime must not contain synthetic/mock quote generation paths.
! rg -n -F 'nitra.market_ingestion.mock' services/market-ingestion/src/main.rs >/dev/null
! rg -n -F 'rand::thread_rng' services/market-ingestion/src/main.rs >/dev/null
! rg -n -F 'gen_range(' services/market-ingestion/src/main.rs >/dev/null
! rg -n 'CONNECTOR_MODE", "mock"' services/market-ingestion/src/main.rs >/dev/null

# Guardrail: runtime source tag is venue-derived and not a mock constant.
rg -n 'nitra\.market_ingestion\.\{\}' services/market-ingestion/src/main.rs >/dev/null

echo "[dev-00009] checks passed"
