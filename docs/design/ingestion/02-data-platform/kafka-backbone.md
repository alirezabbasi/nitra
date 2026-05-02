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

## Kafka Topic SLO + Right-Sizing Contract (DEV-00074)

- Policy contract table:
  - `control_panel_ingestion_kafka_topic_policy`
- Policy fields per topic:
  - `target_partitions`, `retention_ms`, `cleanup_policy`,
  - `max_consumer_lag_messages`, `max_consumer_lag_seconds`,
  - `min_insync_replicas`, `enabled`.
- Enforcement checks:
  - topic must exist in `infra/kafka/topics.csv`,
  - bounded partitions/retention/lag SLO/ISR values,
  - privileged updates require operator role + justification.
- Control-plane mutation endpoint:
  - `POST /api/v1/control-panel/ingestion/kafka-topic-policy`

## Schema Compatibility CI Gate Contract (DEV-00076)

- Gate scripts:
  - `scripts/kafka/schema_compat_gate.py`
  - `scripts/kafka/schema_compat_gate.sh`
- Gate validates backward/forward compatibility for every topic listed in `infra/kafka/topics.csv` by checking:
  - current schema file exists under `infra/kafka/schemas/current`,
  - baseline schema file exists under `infra/kafka/schemas/baseline`,
  - object property type stability,
  - no backward-incompatible required-field additions,
  - no forward-incompatible required-field removals.
- Control-plane mutation endpoint:
  - `POST /api/v1/control-panel/ingestion/kafka-schema-compat-check`


## Control-Panel Kafka Module Consolidation (DEV-00126)

- Control-panel Kafka module consolidates delivery slices from:
  - `DEV-00074` topic SLO + partition/retention policy,
  - `DEV-00075` lag recovery + dead-letter replay workflows,
  - `DEV-00076` schema compatibility CI gate.
- Companion-scope verification target:
  - `make test-dev-0126`.
