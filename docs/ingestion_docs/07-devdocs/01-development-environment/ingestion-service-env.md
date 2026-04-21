# Ingestion Service Environment Variables (DEV-00005)

This page defines environment variables for the minimal ingestion runtime wired in NITRA compose.

## market-ingestion

- `KAFKA_BROKERS` default `kafka:9092`
- `INGESTION_RAW_TOPIC` default `raw.market.oanda`
- `INGESTION_HEALTH_TOPIC` default `connector.health`
- `INGESTION_VENUE` default `oanda`
- `INGESTION_SYMBOL` default `EUR_USD`
- `INGESTION_INTERVAL_SECS` default `1.0`

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
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)

## backfill-worker

- `KAFKA_BROKERS` default `kafka:9092`
- `BACKFILL_INPUT_TOPIC` default `gap.events`
- `BACKFILL_REPLAY_TOPIC` default `replay.commands`
- `BACKFILL_GROUP_ID` default `nitra-backfill-worker-v1`
- `BACKFILL_TARGET_GROUP` default `nitra-market-normalization-v1`
- `DATABASE_URL` required (compose sets from `POSTGRES_*`)
