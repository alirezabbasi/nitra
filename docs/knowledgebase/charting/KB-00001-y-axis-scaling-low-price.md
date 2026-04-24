# KB-00001: Y-Axis Scaling Looks Wrong for Low-Price Instruments

## Problem

Low-price instruments (for example `EURUSD`, `XRPUSD`, `ADAUSD`) appeared vertically compressed or visually "flat" while higher-price instruments (for example `BTCUSD`) looked normal.

## Symptoms

- Switching symbols did not visibly reset chart vertical behavior.
- Debug runs showed calculated instrument range was narrow and correct, but rendered axis still appeared broad.
- Candles around `1.x` or below looked almost like a flat line.

## RCA

This issue had multiple contributors during debugging:

1. Precision mismatch for low-price symbols.
- Runtime default precision could collapse tiny candle deltas into visually flat movement.

2. Y-range callback reliability.
- In some client/runtime paths, pane range callbacks were not consistently applied (`createRange` callback hit count remained `0` in diagnostics).

3. Scale perception mismatch.
- Even with correct data range, low decimal precision can make movement look compressed.

## Resolution

Implemented and kept:

1. Instrument-aware precision application in chart runtime.
- Use `setPriceVolumePrecision(pricePrecision, volumePrecision)` when available.
- Keep `setSymbol({ pricePrecision, volumePrecision })` as fallback.
- Infer precision by symbol/price magnitude (for example JPY pairs use lower decimal precision than sub-1 instruments).

2. Dynamic pane targeting for custom range hooks.
- Discover pane ids via `getPaneOptions()` and apply range handlers against discovered pane ids.
- Keep non-id fallback `setPaneOptions` path for runtime compatibility.

3. Auto/visible range modes preserved.
- Auto mode recalculates by current instrument visible set.
- Visible mode triggered only by explicit right-axis double-click fit action.

Removed after troubleshooting:

- Temporary debug overlay and telemetry UI (range callback hits, pane ids, applied precision diagnostics).

## Validation

- Run `tests/dev-0015/run.sh`.
- Switch between high-price and low-price symbols.
- Confirm low-price symbols render non-flat movement and do not inherit prior symbol scaling behavior.

## Guardrails

- Keep symbol/timeframe switch path as the single source for applying precision and auto range.
- Avoid long-lived debug overlays in production UI; use short-lived instrumentation only.
- If scaling regresses again, re-enable callback hit telemetry temporarily in a feature branch.
