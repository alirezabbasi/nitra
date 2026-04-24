# Ingestion Service Environment Variables (DEV-00005)

This page defines environment variables for the minimal ingestion runtime wired in NITRA compose.

## charting

- `CHARTING_PORT` default `8110`
- `CHARTING_TIMEFRAME` default `1m`
- `CHARTING_DEFAULT_LIMIT` default `300`
- `CHARTING_REFRESH_SECS` default `5`
- `OANDA_API_TOKEN` optional; required for strict venue-history backfill on OANDA symbols
- `OANDA_REST_URL` default `https://api-fxpractice.oanda.com`
- `COINBASE_REST_URL` default `https://api.exchange.coinbase.com`
- `COINBASE_PUBLIC_REST_URL` default `https://api.coinbase.com` (fallback public candles route)
- `CAPITAL_API_URL` (required for Capital history adapter)
- `CAPITAL_API_KEY` (required for Capital history adapter)
- `CAPITAL_IDENTIFIER` (required for Capital history adapter)
- `CAPITAL_API_PASSWORD` (required for Capital history adapter)
- `CAPITAL_EPIC_MAP` optional JSON map for canonical symbol -> epic (for example `{"EURUSD":"CS.D.EURUSD.MINI.IP"}`)
- `CHARTING_VENUE_FETCH_TIMEOUT_SECS` default `8` (per-request timeout for venue history backfill calls)
- `CHARTING_VENUE_FETCH_MAX_ERRORS` default `3` (fail-fast threshold before aborting long backfill loops)

## market-ingestion services (parallel)

The compose runtime starts three ingestion services simultaneously:

- `market-ingestion-oanda` (OANDA)
- `market-ingestion-capital` (CAPITAL)
- `market-ingestion-coinbase` (COINBASE)

Shared:

- `KAFKA_BROKERS` default `kafka:9092`
- `INGESTION_HEALTH_TOPIC` default `connector.health`

OANDA profile:

- `OANDA_RAW_TOPIC` default `raw.market.oanda`
- `OANDA_DEFAULT_INSTRUMENT` default `EURUSD`
- `OANDA_ENABLED_INSTRUMENTS` default `EURUSD,GBPUSD,USDJPY`
- `OANDA_POLL_INTERVAL_SECS` default `1.0`
- `OANDA_STREAM_URL`
- `OANDA_REST_URL` default `https://api-fxpractice.oanda.com` (used for pricing REST fallback/normalization of stream host)
- `OANDA_ACCOUNT_ID`
- `OANDA_API_TOKEN`

CAPITAL profile:

- `CAPITAL_RAW_TOPIC` default `raw.market.capital`
- `CAPITAL_DEFAULT_INSTRUMENT` default `EURUSD`
- `CAPITAL_ENABLED_INSTRUMENTS` default `EURUSD,GBPUSD`
- `CAPITAL_POLL_INTERVAL_SECS` default `1.0`
- `CAPITAL_API_URL`
- `CAPITAL_API_KEY`
- `CAPITAL_IDENTIFIER`
- `CAPITAL_API_PASSWORD`
- `CAPITAL_EPIC_ALLOWLIST`
- `CAPITAL_EPIC_MAP` optional JSON map for canonical symbol -> venue epic (for example `{"EURUSD":"CS.D.EURUSD.MINI.IP"}`)

Note:

- Pair symbols are emitted in compact alphanumeric format only (for example `EURUSD`, `GBPUSD`, `BTCUSD`) with no `_`, `-`, or dot separators.
- Synthetic/mock quote generation is prohibited in runtime ingestion services.
- `CONNECTOR_MODE=mock` is explicitly rejected by `market-ingestion` (fail-closed startup behavior).

COINBASE profile:

- `COINBASE_RAW_TOPIC` default `raw.market.coinbase`
- `COINBASE_DEFAULT_INSTRUMENT` default `BTCUSD`
- `COINBASE_ENABLED_INSTRUMENTS` default `BTCUSD,ETHUSD,SOLUSD,ADAUSD,XRPUSD`
- `COINBASE_POLL_INTERVAL_SECS` default `1.0`
- `COINBASE_WS_URL`
- `COINBASE_REST_URL` default `https://api.exchange.coinbase.com`
- `COINBASE_PUBLIC_REST_URL` default `https://api.coinbase.com` (spot-price fallback when Exchange ticker endpoint is unavailable per product/runtime)
- `COINBASE_PRODUCT_ALLOWLIST`
- `COINBASE_CHANNELS`

## market-normalization

- `KAFKA_BROKERS` default `kafka:9092`
- `NORMALIZER_INPUT_TOPICS` default `raw.market.oanda,raw.market.capital,raw.market.coinbase`
- `NORMALIZER_OUTPUT_TOPIC` default `normalized.quote.fx`
- `NORMALIZER_GROUP_ID` default `nitra-market-normalization-v1`
- `NORMALIZER_SYMBOL_REGISTRY_PATH` default `/app/ingestion/registry.v1.json`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

## bar-aggregation

- `KAFKA_BROKERS` default `kafka:9092`
- `BAR_INPUT_TOPIC` default `normalized.quote.fx`
- `BAR_OUTPUT_TOPIC` default `bar.1m`
- `BAR_GROUP_ID` default `nitra-bar-aggregation-v1`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

## gap-detection

- `KAFKA_BROKERS` default `kafka:9092`
- `GAP_INPUT_TOPIC` default `bar.1m`
- `GAP_OUTPUT_TOPIC` default `gap.events`
- `GAP_GROUP_ID` default `nitra-gap-detection-v1`
- `GAP_STARTUP_SCAN_ENABLED` default `true`
- `GAP_STARTUP_COVERAGE_DAYS` default `90`
- `GAP_ACTIVE_MARKET_DB_LOOKBACK_HOURS` default `24`
- `GAP_SYMBOL_REGISTRY_PATH` default `/etc/nitra/registry.v1.json`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

## backfill-worker

- `KAFKA_BROKERS` default `kafka:9092`
- `BACKFILL_INPUT_TOPIC` default `gap.events`
- `BACKFILL_REPLAY_TOPIC` default `replay.commands`
- `BACKFILL_GROUP_ID` default `nitra-backfill-worker-v1`
- `BACKFILL_TARGET_GROUP` default `nitra-market-normalization-v1`
- `BACKFILL_STARTUP_PROCESS_OPEN_GAPS` default `true`
- `BACKFILL_FETCH_CHUNK_MINUTES` default `60`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

## replay-controller

- `KAFKA_BROKERS` default `kafka:9092`
- `REPLAY_INPUT_TOPIC` default `replay.commands`
- `REPLAY_GROUP_ID` default `nitra-replay-controller-v1`
- `REPLAY_SYMBOL_REGISTRY_PATH` default `/etc/nitra/registry.v1.json`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

Notes:
- Current replay executor rebuilds `1m` bars from available `raw_tick` source data in the requested range and updates `backfill_jobs` + `replay_audit` statuses accordingly.
