# DEV-00003: Kafka Contracts and Topic Bootstrap for NITRA Ingestion

## Status

Done

## Summary

Define and wire the minimal Kafka topic/bootstrap contract for NITRA ingestion flow, aligned with NITRA naming and service boundaries.

## Scope

- Define ingestion topic set for raw -> normalized -> bars -> gaps/replay paths.
- Add bootstrap script/automation compatible with NITRA Docker-first runtime.
- Document topic names, retention intent, and consumer-group expectations.

## Hard Exclusions

- No Redpanda-specific operational dependencies in baseline NITRA workflow.
- No unused topic families copied from BarsFP without an active consumer/producer path.

## Deliverables

1. Kafka topic contract document in NITRA docs.
2. Repeatable topic bootstrap mechanism in repository tooling.
3. Step test validating bootstrap idempotency.

## Acceptance Criteria

- `docker compose up -d` + bootstrap path works on clean dev setup.
- Topic creation is idempotent.
- Only topics needed by implemented ingestion flow are created.

## Evidence

- Topic contract: `docs/ingestion_docs/02-data-platform/kafka-backbone.md`
- Topic catalog: `infra/kafka/topics.csv`
- Bootstrap mechanism: `scripts/kafka/bootstrap-topics.sh`
- Step test: `tests/dev-00003/run.sh`
