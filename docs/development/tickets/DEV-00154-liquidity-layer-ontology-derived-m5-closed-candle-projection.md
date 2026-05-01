# DEV-00154: Liquidity Layer ontology-derived M5 closed-candle projection

## Status

Done (2026-05-01)

## Goal

Replace chart-side heuristic liquidity-layer generation with backend ontology-derived projection over closed `M5` candles for `today + yesterday`, and make chart rendering consume that projection.

## Scope

- Add backend projection endpoint with deterministic `M5` closed-candle windowing.
- Build overlay payload on backend (minor/major segments + markers).
- Refactor chart liquidity layer to consume backend payload.
- Enforce update cadence on closed `M5` boundaries instead of per-tick recomputation.

## Acceptance Criteria

- Liquidity layer source is backend API, not local heuristic model.
- Projection window is `today + yesterday`.
- Projection timeframe is closed `M5` candles.
- Chart overlay refreshes only when closed `M5` boundary advances or symbol changes.

## Verification

- `PYTHONPYCACHEPREFIX=/tmp/pycache python -m py_compile services/charting/app.py`
- `docker compose up -d --build control-panel`
- `curl -sS "http://localhost:8110/api/v1/liquidity-layer?venue=oanda&symbol=GBPUSD"`
- `curl -sS "http://localhost:8110/charting?venue=oanda&symbol=GBPUSD&timeframe=5m" | rg -n "api/v1/liquidity-layer|TF:M5\\(closed\\)"`

## Delivered Artifacts

- `services/charting/app.py`
  - `GET /api/v1/liquidity-layer` endpoint
  - closed `M5` window aggregation helpers
  - backend ontology projection + overlay payload generation
- `services/charting/static/index.html`
  - liquidity layer now fetches backend payload
  - closed-M5 refresh gating and summary update
- `docs/development/debugging/BUG-00009.md`
  - bug status and fix evidence updated
