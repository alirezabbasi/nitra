# DEV-00007 Live Ingestion Dev Runbook

This runbook is for development-only startup and validation of NITRA live ingestion flow.

## Scope

Covered path:
- `market-ingestion-oanda` + `market-ingestion-capital` + `market-ingestion-coinbase` -> `market-normalization` -> `bar-aggregation` -> `gap-detection` -> `backfill-worker` -> `replay-controller`

Required baseline:
- Kafka topics from `infra/kafka/topics.csv`
- Timescale init migrations from `infra/timescaledb/init/`

## Prerequisites

1. Docker daemon is running.
2. Repository root is current working directory.
3. `.env` exists.

Create `.env` when missing:

```bash
cp .env.example .env
```

## Startup

1. Start platform containers:

```bash
make up
```

2. Bootstrap ingestion topics (idempotent):

```bash
make kafka-bootstrap
```

3. Confirm key services are running:

```bash
docker compose ps timescaledb kafka charting market-ingestion-oanda market-ingestion-capital market-ingestion-coinbase market-normalization bar-aggregation gap-detection backfill-worker replay-controller
```

4. Optional logs (follow):

```bash
docker compose logs -f --tail=200 charting market-ingestion-oanda market-ingestion-capital market-ingestion-coinbase market-normalization bar-aggregation gap-detection backfill-worker replay-controller
```

Charting UI:

```bash
http://localhost:${CHARTING_PORT:-8110}/
```

## Validation Checklist

Use these checks in order.

1. Kafka topics exist:

```bash
make kafka-topics
```

2. Raw events are persisted:

```bash
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) AS raw_tick_rows FROM raw_tick;"
```

3. Normalized->bar path is active:

```bash
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT venue, canonical_symbol, bucket_start, open, high, low, close FROM ohlcv_bar ORDER BY bucket_start DESC LIMIT 10;"
```

4. Replay/idempotency ledger is populated:

```bash
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT service_name, COUNT(*) AS rows FROM processed_message_ledger GROUP BY service_name ORDER BY service_name;"
```

5. Startup coverage state and gap/backfill lifecycle tables are present:

```bash
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) AS tracked_symbols FROM coverage_state;"
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT status, COUNT(*) FROM gap_log GROUP BY status ORDER BY status;"
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT status, COUNT(*) FROM backfill_jobs GROUP BY status ORDER BY status;"
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT status, COUNT(*) FROM replay_audit GROUP BY status ORDER BY status;"
```

6. Venue adapter live probe (DEV-00014 hardening):

```bash
curl -sS -X POST http://localhost:${CHARTING_PORT:-8110}/api/v1/backfill/adapter-check -H 'content-type: application/json' -d '{"venue":"coinbase","symbol":"BTCUSD"}' | jq
curl -sS -X POST http://localhost:${CHARTING_PORT:-8110}/api/v1/backfill/adapter-check -H 'content-type: application/json' -d '{"venue":"oanda","symbol":"EURUSD"}' | jq
curl -sS -X POST http://localhost:${CHARTING_PORT:-8110}/api/v1/backfill/adapter-check -H 'content-type: application/json' -d '{"venue":"capital","symbol":"EURUSD"}' | jq
```

7. Replay source-depth verification (BUG-00006 fix path):

```bash
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT status, COUNT(*) FROM backfill_jobs GROUP BY status ORDER BY status;"
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT status, COUNT(*) FROM replay_audit GROUP BY status ORDER BY status;"
```

8. Optional DEV-00006 checks:

```bash
make test-dev-00006
```

9. Optional duplicate-injection integration drill (requires Docker access):

```bash
DEV00006_INTEGRATION=1 tests/dev-00006/run.sh
```

## Safe Stop / Restart

Safe stop (preserves volumes/data):

```bash
docker compose stop
```

Safe restart:

```bash
docker compose restart
```

Do not use destructive commands such as `docker compose down -v`.

## Rollback / Fallback

If ingestion services are unstable:

1. Stop only ingestion services:

```bash
docker compose stop market-ingestion-oanda market-ingestion-capital market-ingestion-coinbase market-normalization bar-aggregation gap-detection backfill-worker replay-controller
```

2. Keep core stateful services running (`timescaledb`, `kafka`) for investigation.
3. Review service logs and fix config/code issues.
4. Restart ingestion services only:

```bash
docker compose up -d --build market-ingestion-oanda market-ingestion-capital market-ingestion-coinbase market-normalization bar-aggregation gap-detection backfill-worker replay-controller
```

## Troubleshooting

1. `kafka-bootstrap` fails:
- Ensure Kafka is healthy: `docker compose ps kafka`
- Retry: `make kafka-bootstrap`

2. No rows in `raw_tick`:
- Check ingestion logs for all three connectors (`market-ingestion-oanda`, `market-ingestion-capital`, `market-ingestion-coinbase`).
- Confirm topic alignment: `raw.market.oanda`, `raw.market.capital`, `raw.market.coinbase`.

3. `raw_tick` grows but `ohlcv_bar` empty:
- Check `market-normalization` and `bar-aggregation` logs.
- Confirm `normalized.quote.fx` and `bar.1m` topic names.

4. Duplicate side effects suspected:
- Run `make test-dev-00006`.
- Inspect ledger:

```bash
docker compose exec -T timescaledb psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT service_name, message_id, source_topic, source_partition, source_offset, processed_at FROM processed_message_ledger ORDER BY processed_at DESC LIMIT 30;"
```

5. DB connection errors in ingestion services:
- Verify `POSTGRES_*` values in `.env`.
- Verify compose `DATABASE_URL` interpolation resolved in `docker compose config`.
