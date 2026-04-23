#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path("services").resolve()))

from ingestion import mock_pricing as mod

assert mod.initial_price("EURUSD") < 10, "EURUSD base price should be FX-like"
assert mod.initial_price("BTCUSD") > 1000, "BTCUSD base price should be crypto-like"
assert mod.initial_price("BTCUSD") != mod.initial_price("EURUSD"), "BTC and EURUSD must not share the same base"

assert mod.infer_asset_class("BTCUSD") == "crypto"
assert mod.infer_asset_class("EURUSD") == "fx"

assert mod.price_precision("BTCUSD") == 2
assert mod.price_precision("EURUSD") == 5
assert mod.price_precision("USDJPY") == 3

assert mod.step_amount("BTCUSD", 67000.0) > mod.step_amount("EURUSD", 1.08)
assert mod.spread_amount("BTCUSD", 67000.0) > mod.spread_amount("EURUSD", 1.08)

print("[dev-00009] checks passed")
PY
