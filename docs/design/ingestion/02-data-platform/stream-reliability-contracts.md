# Stream Reliability Contracts (EPIC-02)

## Retry Contract

- Delivery model is at-least-once.
- Critical consumers use explicit/manual offset commits (`enable.auto.commit=false`).
- Offsets are committed only after successful deterministic handling or explicit deterministic drop paths.
- Failed processing attempts attach/update `RetryMetadata`.
- `next_retry_action(attempt_count, max_retries)` determines when to move to DLQ.

## Replay Guard Contract

- `Envelope.message_id` is the replay guard identity for message-level deduplication.
- `processed_message_ledger` in Timescale records:
  - `service_name`
  - `message_id`
  - source topic/partition/offset
  - processed timestamp
- Replay guard flow:
  - if `(service_name, message_id)` already exists, skip side effects and commit offset
  - otherwise process side effects, persist ledger row, then commit offset
- Enforced services in EPIC-12:
  - `normalizer`
  - `bar_engine`
  - `gap_engine`
  - `backfill_worker`
  - `risk_gateway`
  - `oms`

## DLQ Contract

- DLQ topic naming: `<source-topic>.dlq`.
- Every primary topic must have a provisioned DLQ partner.
- DLQ events preserve envelope and retry metadata for forensic replay.

## Replay Contract

`ReplayRequest` fields:
- `replay_id`
- `source_topic`
- `start_offset`, `end_offset` (optional)
- `start_ts`, `end_ts` (optional)
- `target_consumer_group`
- `dry_run`
- `requested_by`

`ReplayResult` fields:
- replay identity and source/target
- moved message count
- start/completion timestamps
- optional terminal error

## Schema Versioning

`Envelope<T>` includes `schema_version` and explicit headers to support controlled evolution.

## DLQ Recovery + Replay Hardening Contract (DEV-00075)

- Lag recovery request contract:
  - `POST /api/v1/control-panel/ingestion/kafka-lag-recovery`
  - persists to `control_panel_ingestion_kafka_lag_recovery_log`.
- Dead-letter replay request contract:
  - `POST /api/v1/control-panel/ingestion/kafka-dead-letter-replay`
  - persists to `control_panel_ingestion_kafka_dead_letter_replay_log`.
- Guardrails:
  - allowed source topics must exist in `infra/kafka/topics.csv`,
  - DLQ naming enforcement (`*.dlq`),
  - bounded lag/replay volumes and bounded replay offset range validation,
  - privileged updates require operator role + justification + audit logging.


## Control-Panel Kafka Module Companion (DEV-00126)

- Kafka recovery/replay/schema controls are exposed as one operator module in control panel ingestion workspace.
- Module-level closeout verification target:
  - `make test-dev-0126`.
