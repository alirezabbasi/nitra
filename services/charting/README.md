# Charting Service Module Map

This service is being refactored from a monolithic `app.py` into focused modules.

## Current Structure

- `app.py`
  - FastAPI app wiring
  - HTTP endpoints
  - control-panel route handlers
  - ingestion/backfill orchestration
- `liquidity_layer.py`
  - ontology-derived M5 liquidity analysis pipeline
  - today+yesterday window bounds
  - M5 aggregation and current-candle augmentation
  - minor/major/active pullback model construction
  - chart overlay segment generation

## Where To Look

- Liquidity ontology logic and rendering payloads:
  - `liquidity_layer.py`
- API contract for liquidity endpoint:
  - `app.py` → `GET /api/v1/liquidity-layer`

## Refactor Direction (Next Splits)

- `control_panel/` package for control-panel endpoints by domain:
  - overview, ingestion, risk, execution, ops, research, config
- `market_data/` package for venue adapters and backfill utilities
- `db/` package for schema bootstrap and SQL access helpers

