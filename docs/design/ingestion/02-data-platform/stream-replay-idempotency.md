# Stream Replay and Idempotency Guarantees (DEV-00006)

This document defines replay/idempotency behavior for the minimal NITRA ingestion consumers.

## Covered Consumers

- `market-normalization`
- `bar-aggregation`
- `gap-detection`
- `backfill-worker`

## Guard Contract

Each covered consumer must:
1. run with `enable_auto_commit=False`
2. check `processed_message_ledger` before side effects
3. skip duplicate message side effects
4. persist ledger row after successful side effects
5. commit Kafka offsets after ledger write

## Duplicate Behavior

- Duplicate message with same `message_id` for the same service is ignored.
- Side effects are not re-emitted or re-persisted for duplicates.
- Offset is still committed for duplicate deliveries.

## Verification

- Static/dev checks: `tests/dev-00006/run.sh`
- Optional live duplicate drill: `DEV00006_INTEGRATION=1 tests/dev-00006/run.sh`
