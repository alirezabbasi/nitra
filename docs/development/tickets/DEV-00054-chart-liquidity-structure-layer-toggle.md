# DEV-00054: Chart Liquidity Structure Layer Toggle

## Goal

Add a selectable chart layer (checkbox toggle) that overlays liquidity-driven pullback/minor/major structure interpretation on any instrument chart.

## Scope

- Add chart UI toggle: `Liquidity Layer` checkbox.
- Compute structure model from live chart bars:
  - pullback detection
  - minor structure pairs
  - major structure escalation when pullback high breaks prior structural highs
  - fractal-style bias adaptation via mirrored bullish interpretation
- Render results as custom kline overlay (`nitraLiquidityLayer`) with:
  - minor pair dashed segments + markers
  - major pair solid segments + markers
- Recompute overlay on market/timeframe/history/live-tick updates.
- Persist layer toggle in UI preferences.

## Files

- `services/charting/static/index.html`
- `tests/dev-0054/run.sh`
- `Makefile`

## Verification

- `make test-dev-0054`
- `make test-dev-0050`
- `make enforce-section-5-1`
