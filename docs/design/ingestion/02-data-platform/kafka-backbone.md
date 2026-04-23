# NITRA Kafka Backbone (Dev Baseline)

This document defines the minimal Kafka topic contract for NITRA ingestion development.

## Scope

- Supports ingestion flow: raw market events -> normalization -> bar aggregation -> gap/backfill signaling.
- Excludes non-essential legacy topic families and monitoring-heavy stack dependencies.

## Topic Contract

Source of truth: `infra/kafka/topics.csv`

| Topic | Purpose | Producer | Consumer Group (primary) |
|---|---|---|---|
| `raw.market.oanda` | Raw OANDA market events | market-ingestion connector | `nitra-market-normalization-v1` |
| `raw.market.capital` | Raw CAPITAL market events | market-ingestion connector | `nitra-market-normalization-v1` |
| `raw.market.coinbase` | Raw COINBASE market events | market-ingestion connector | `nitra-market-normalization-v1` |
| `normalized.quote.fx` | Canonical quote events | market-normalization | `nitra-bar-aggregation-v1` |
| `bar.1m` | Deterministic 1m bars | bar-aggregation | `nitra-gap-detection-v1` |
| `gap.events` | Missing-interval/gap events | gap-detection | `nitra-backfill-worker-v1` |
| `replay.commands` | Replay/backfill command events | backfill-worker/replay control | `nitra-replay-controller-v1` |
| `connector.health` | Connector heartbeat/status telemetry | market-ingestion connector | `nitra-ops-monitor-v1` |

## Bootstrap

Use the idempotent bootstrap script:

```bash
scripts/kafka/bootstrap-topics.sh
```

Optional dry run:

```bash
DRY_RUN=1 scripts/kafka/bootstrap-topics.sh
```

The script uses `--if-not-exists`, making repeated runs safe.

## Operational Notes

- Start runtime first: `docker compose up -d`.
- Bootstrap is intentionally Kafka-native and avoids Redpanda-specific dependencies.
- Only topics required by currently wired ingestion path are defined.
