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
3. User selects an instrument from the left market list.
4. Web app calls `/api/v1/bars/hot?venue=...&symbol=...&limit=...`.
5. Service queries TimescaleDB table `ohlcv_bar` and returns chart-ready candles.
6. Web app polls `/api/v1/ticks/hot` and synthesizes/updates a provisional current candle between persisted bar updates.

## API Contract

- `GET /health`
  - returns `{"status":"ok","service":"charting"}`

- `GET /api/v1/config`
  - returns defaults from env (`timeframe`, `limit`, refresh interval)

- `GET /api/v1/markets/available?timeframe=1m`
  - returns list of available `venue` and `canonical_symbol` pairs from `ohlcv_bar` for selectable instruments

- `GET /api/v1/bars/hot?venue=<venue>&symbol=<symbol>&timeframe=1m&limit=300`
  - returns ordered OHLCV candlestick payload for UI rendering

- `GET /api/v1/ticks/hot?venue=<venue>&symbol=<symbol>&since_ms=<unix_ms>&limit=500`
  - returns incremental tick prices from `raw_tick` used to move the current candle in real time

## Environment Variables

- `CHARTING_PORT` (compose host exposure)
- `CHARTING_TIMEFRAME`
- `CHARTING_DEFAULT_LIMIT`
- `CHARTING_REFRESH_SECS`
- `DATABASE_URL` (injected by compose)

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
