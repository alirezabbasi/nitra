# Migration Map: `barflow` -> `barsfp`

## Objective

Preserve proven behavior from `barflow` while replacing runtime/storage foundations for scale and reliability.

## Continuity Mapping

- Legacy `EPIC-01..09` data quality and operability controls are retained.
- Legacy contracts (idempotency, gap repair, retention, SLOs, closure gate) are upgraded to Redpanda + Rust-first runtime.
- Legacy docs become historical references; `barsfp/docs` is the new source of truth.

## Replacement Mapping

- Python connectors -> Rust connectors.
- Redis streams -> Redpanda topics.
- Postgres-only hot/cold compromise -> Timescale hot + ClickHouse cold + MinIO lake.
- Manual mixed ops controls -> explicit SLO gate automation.

## Migration Method

1. Keep contracts stable.
2. Replace one layer per epic.
3. Validate via replay, determinism, and reconciliation checks.
4. Cut over only after shadow parity or better.

## No-Regret Constraints

- Never skip replayability.
- Never bypass risk controls.
- Never promote to live without runbook drill evidence.
