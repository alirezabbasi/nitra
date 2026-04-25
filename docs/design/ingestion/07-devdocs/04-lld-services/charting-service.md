# Charting Service (`charting`)

## Purpose

`charting` is a browser-facing candlestick dashboard for the NITRA hot store.
It renders Kline-style charts per market (`venue + canonical_symbol`) directly from `ohlcv_bar` data.
Instrument selection is populated dynamically from database-backed market discovery.

## Runtime Placement

- Compose service: `charting`
- Container port: `8080`
- Host port: `${CHARTING_PORT:-8110}`
- URL: `http://localhost:8110/`

## Data Path

1. Browser opens `/` and loads the charting web app.
2. Web app calls `/api/v1/markets/available`.
3. User selects an instrument from the header combobox (searchable + clickable dropdown list).
4. User can open the header `Settings` (gear) modal to:
   - add/select venue definitions from DB,
   - add markets (`venue + symbol + asset_class`),
   - start ingestion for a selected market (`ingest_enabled=true`).
4. User selects timeframe from header dropdown (`1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`).
5. Web app calls `/api/v1/bars/hot?venue=...&symbol=...&timeframe=...&limit=...`.
6. Service queries TimescaleDB table `ohlcv_bar` and returns chart-ready candles.
7. If higher timeframe bars are missing, UI derives them from available `1m` bars.
8. Web app polls `/api/v1/ticks/hot` and synthesizes/updates a provisional current candle between persisted bar updates.
9. During left-edge exploration, web app calls `/api/v1/bars/history` to lazy-load older ranges without dropping live mode state.
10. User can trigger `Backfill 90d` from header; service enforces strict 90-day `1m` continuity:
   - rebuild from `raw_tick` first,
   - detect any missing `1m` buckets,
   - fetch missing ranges from venue history adapters (`oanda`, `capital`, `coinbase` with exchange->public fallback),
   - apply continuity policy by market profile:
     - FX (`oanda`/`capital`, non-crypto): weekend closed minutes are excluded from required continuity
     - crypto: all minutes are required (`24/7`)
   - return incomplete status if any required minute remains missing.

## API Contract

- `GET /health`
  - returns `{"status":"ok","service":"charting"}`

- `GET /api/v1/config`
  - returns defaults from env (`timeframe`, `limit`, refresh interval)

- `GET /api/v1/markets/available?timeframe=1m`
  - returns DB-configured and data-backed markets for selectable instruments
  - includes `ingest_enabled` + `asset_class`

- `GET /api/v1/venues`
  - returns DB-configured venue list

- `GET /api/v1/venues/{venue}/markets`
  - returns DB-configured market list for one venue with latest bar metadata

- `POST /api/v1/venues`
  - create/activate a venue entry (currently supports `oanda`, `capital`, `coinbase`)

- `POST /api/v1/venues/{venue}/markets`
  - upsert market configuration (`symbol`, `asset_class`, `enabled`, `ingest_enabled`)

- `POST /api/v1/ingestion/start`
  - marks selected `venue + symbol` as enabled for ingestion in DB config

- `GET /api/v1/bars/hot?venue=<venue>&symbol=<symbol>&timeframe=1m&limit=300`
  - returns ordered OHLCV candlestick payload for UI rendering

- `GET /api/v1/bars/history?venue=<venue>&symbol=<symbol>&timeframe=1m&before_s=<unix_s>&limit=500`
  - returns older ordered OHLCV payload plus `has_more` for left-edge lazy pagination

- `GET /api/v1/ticks/hot?venue=<venue>&symbol=<symbol>&since_ms=<unix_ms>&limit=500`
  - returns incremental tick prices from `raw_tick` used to move the current candle in real time

- `POST /api/v1/backfill/90d`
  - request body: `{"venue":"<venue>","symbol":"<symbol>"}`
  - behavior:
    - checks last 90 days (closed-minute window) in `ohlcv_bar` for selected `venue + symbol`
    - if any `1m` gap exists, first rebuilds from `raw_tick`, then fetches missing ranges from venue history
    - requires full required-continuity window to report success (`complete_90d_1m=true`)
  - returns coverage counts (`missing_before_fetch_count`, `missing_after_fetch_count`) and adapter status

Note:
- If venue adapter is unavailable or venue does not provide full minute history, endpoint returns explicit incomplete status with remaining missing-minute count.

## Environment Variables

- `CHARTING_PORT` (compose host exposure)
- `CHARTING_TIMEFRAME`
- `CHARTING_DEFAULT_LIMIT`
- `CHARTING_REFRESH_SECS`
- `DATABASE_URL` (injected by compose)
- `OANDA_API_TOKEN` (for OANDA history fetch adapter)
- `OANDA_REST_URL` (default `https://api-fxpractice.oanda.com`)
- `COINBASE_REST_URL` (default `https://api.exchange.coinbase.com`)
- `COINBASE_PUBLIC_REST_URL` (default `https://api.coinbase.com`)
- `CAPITAL_API_URL`
- `CAPITAL_API_KEY`
- `CAPITAL_IDENTIFIER`
- `CAPITAL_API_PASSWORD`
- `CAPITAL_EPIC_MAP` (optional symbol->epic JSON mapping)
- `CHARTING_VENUE_FETCH_TIMEOUT_SECS` (default `8`)
- `CHARTING_VENUE_FETCH_MAX_ERRORS` (default `3`)

## Implementation Files

- `services/charting/Dockerfile`
- `services/charting/requirements.txt`
- `services/charting/app.py`
- `services/charting/static/index.html`

## Verification

- `make up`
- `docker compose ps charting`
- `curl -sS http://localhost:8110/health`
- open `http://localhost:8110/`

## UX Controls Implemented (`DEV-00015`)

- Realtime return button (`scrollToRealTime`)
- Jump to timestamp and data index (`scrollToTimestamp`, `scrollToDataIndex`)
- Zoom anchor mode (`cursor` / `last_bar`)
- Bar density control (`setBarSpace`)
- Right-edge breathing room (`setOffsetRightDistance`)
- Left/right min visible-bar controls
- Scroll/zoom lock toggles
- Crosshair/range metadata updates via chart action subscriptions
- Pixel/value coordinate inspector (`convertFromPixel`)
- Snapshot export (`getConvertPictureUrl`)
- Locale/timezone controls
- Number format mode toggle (`compact`/`raw`)
