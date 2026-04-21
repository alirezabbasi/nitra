# Chart UI Service (`chart-ui`)

## Purpose

`chart-ui` is a dedicated web charting surface for live and historical OHLCV visualization.

- It is intentionally separated from `query-api`.
- `query-api` remains a pure data API.
- `chart-ui` serves browser assets and proxies API calls to avoid CORS complexity.

## Runtime Placement

- Compose service: `chart-ui`
- Container port: `8081`
- Host port: `${CHART_UI_PORT:-8110}`

Access:

- `http://localhost:8110/` (default)

## Data Path

1. Browser opens `chart-ui` static page.
2. Page requests `/api/v1/bars/hot` or `/api/v1/bars/cold`.
3. Page requests `/api/v1/markets/available` to populate market selector options.
4. NGINX reverse-proxy forwards `/api/*` to `http://query-api:8104/*`.
5. `query-api` reads from:
   - TimescaleDB (`ohlcv_bar`) for hot queries
   - ClickHouse (`bars_hist`) for cold queries
   - TimescaleDB (`raw_tick`) for live tick polling (`/v1/ticks/hot`)
   - TimescaleDB (`ohlcv_bar`) for available market discovery (`/v1/markets/available`)

## Service Files

- `services/chart_ui/Dockerfile`
- `services/chart_ui/nginx.conf`
- `services/chart_ui/www/index.html`

## UI Functional Scope

- Minimal chart-first shell:
  - compact top command bar,
  - center chart workspace,
  - lightweight runtime footer status.
- Layout behavior:
  - viewport-fitted page (`100dvh`) with no document scrolling.
- Core query controls:
  - combined market selector (`venue + symbol` in one dropdown),
  - timeframe, source, limit, refresh interval.
- Market switch behavior:
  - changing the combined `venue + symbol` selector triggers market context switch and data reload.
  - selector options are dynamically loaded from `/v1/markets/available` and only include markets with database data.
- Source switch:
  - Hot (`/api/v1/bars/hot`)
  - Cold (`/api/v1/bars/cold`)
- Auto-refresh interval for ongoing market updates.
- Candlestick rendering from `open/high/low/close`.
  - latest/provisional candle follows the same bullish/bearish color rules as all other candles (no separate override color).
- Chart interaction behavior:
  - drag on chart pans history back/forward,
  - mouse wheel zooms candle density,
  - right-side price axis is rendered with current price line and label.
- Live session metrics:
  - O/H/L/C header,
  - session change display,
  - tick count and bar count runtime indicators.
- Tick-driven liveness for hot mode:
  - UI polls `/api/v1/ticks/hot`.
  - UI builds a provisional current-minute candle from live ticks.
  - Provisional candle is merged with persisted bars so chart moves between bar finalizations.
- Theme and personalization:
  - chart-wide light/dark mode toggle is available on the top bar,
  - settings modal allows separate color customization for light and dark palettes (candles, grid, chart background, price line, price label),
  - preferences are persisted in browser local storage and restored on next load.

## Configuration Contract

- `.env.example`:
  - `CHART_UI_PORT=8110`

No API secrets are embedded in the UI. Data access remains through existing backend services.

## Health and Debug

- Container health check: HTTP `GET /` on port `8081`
- Logs:
  - `make chart-ui-logs`
  - `docker compose logs -f chart-ui`

## Test Coverage

- `tests/epic-22/run.sh` validates:
  - service startup and health,
  - static page response,
  - reverse proxy to `/api/health`,
  - hot bars endpoint reachability through chart-ui proxy.
