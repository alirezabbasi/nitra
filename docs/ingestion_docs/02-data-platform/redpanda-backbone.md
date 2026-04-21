# Redpanda Backbone (EPIC-02)

## Goal

Provide a deterministic, dockerized stream backbone with bootstrap automation for topics and DLQ counterparts.

## Bootstrap Components

- `docker-compose.yml` service: `redpanda`
- `docker-compose.yml` service: `redpanda-console`
- `docker-compose.yml` service: `redpanda-topic-init`
- Bootstrap script: `scripts/redpanda/bootstrap-topics.sh`
- Topic catalog: `infra/redpanda/topics.csv`

## Topic Strategy

- Each primary topic has a matching DLQ topic with `.dlq` suffix.
- Topic definitions include partitions, replication factor, cleanup policy, and retention settings.
- Bootstrap is idempotent: create if missing, then enforce configs.
- Current baseline uses non-expiring retention (`retention_ms=-1`, `retention_bytes=-1`) to preserve data permanence.

## Baseline Topic Set

- `raw.market.oanda`
- `raw.market.capital`
- `raw.market.coinbase`
- `normalized.tick.fx`
- `normalized.trade.fx`
- `normalized.quote.fx`
- `bar.1s`
- `bar.1m`
- `gap.events`
- `risk.events`
- `execution.orders`
- `execution.fills`
- `connector.health`
- `replay.commands`
- `replay.events`

Each receives a corresponding `.dlq` topic.

## Operation

- Start stack: `docker compose up -d`
- Verify: `docker compose ps`
- Bootstrap/re-bootstrap topics: `make stream-bootstrap`
