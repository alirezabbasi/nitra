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

## Deterministic Quarantine Pipeline (DEV-00077)

- `market-normalization` must quarantine malformed or schema-invalid inbound envelopes/events instead of silently dropping them.
- Quarantine evidence contract:
  - table: `normalization_quarantine_event`
  - deterministic key: `(source_topic, source_partition, source_offset)`
  - reason taxonomy examples:
    - `invalid_envelope_json`
    - `invalid_envelope_payload`
    - `missing_venue`
    - `missing_broker_symbol`
    - `invalid_event_ts_received`
    - `malformed_market_payload`
- Replay-safe re-ingest flow:
  - reingested messages are marked resolved when `headers.quarantine_reingest=true` and normalization succeeds.
  - resolution state transitions to `reingested` with timestamped evidence.

## Sequence/Order Integrity Verifier (DEV-00078)

- `market-normalization` must persist deterministic sequence/order integrity verdicts for every normalized event.
- Integrity evidence contract:
  - table: `normalization_sequence_integrity_event`
  - deterministic key: `(source_topic, source_partition, source_offset)`
  - source-sequence fields copied from `raw_message_capture`:
    - `source_sequence_id`
    - `source_sequence_numeric`
    - `source_sequence_status`
    - `source_sequence_gap`
  - normalized-order fields:
    - `normalized_event_ts_received`
    - `previous_normalized_event_ts_received`
    - `normalized_order_status` (`initial|ordered|same_ts|retrograde`)
- Integrity verdict contract:
  - `integrity_status`:
    - `pass` when source sequence and normalized order are consistent,
    - `warn` when source sequence is unavailable but normalized order is still tracked,
    - `fail` on source sequence anomalies (`gap|out_of_order|duplicate`) or retrograde normalized ordering.
  - `integrity_reason` stores deterministic human-readable verdict rationale per event.

## 90-Day Startup Coverage Conformance Harness (DEV-00079)

- `gap-detection` startup and periodic coverage scans use a deterministic, policy-aware missing-range harness for the rolling 90-day `10s` window.
- Venue-session edge-case fixture contract:
  - FX venues (`oanda`, `capital`) exclude configured weekend-closed buckets from expected coverage.
  - Crypto venues (for example `coinbase`) remain `24/7` and must report weekend missing buckets as true gaps.
- Session policy env contract consumed by coverage scanner:
  - `FX_WEEKEND_START_ISO_DOW`
  - `FX_WEEKEND_START_HOUR_UTC`
  - `FX_WEEKEND_END_ISO_DOW`
  - `FX_WEEKEND_END_HOUR_UTC`
