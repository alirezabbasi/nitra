# Second-Chain Contracts and Replay Determinism (DEV-00036)

## Scope

Canonical contracts are frozen for the deterministic second chain:
`structure -> features -> signal -> risk -> execution -> portfolio -> journal`.

## Canonical Topics

- `structure.snapshot.v1`
- `features.snapshot.v1`
- `decision.signal_scored.v1` (approved equivalent for `signal.scored.v1`)
- `decision.risk_checked.v1`
- `exec.order_submitted.v1`
- `exec.order_updated.v1`
- `exec.fill_received.v1`
- `portfolio.snapshot.v1`
- `audit.event.v1` (canonical journal/audit domain event contract)

## Required Envelope Contract

Every second-chain event must use repository envelope shape:

- `message_id` (UUID)
- `emitted_at` (RFC3339 timestamp)
- `schema_version` (integer)
- `headers` (object)
- `payload` (object)
- `retry` (object or null)

## Ordering and Idempotency Requirements

- Consumer processing must remain idempotent through `processed_message_ledger` uniqueness on `(service_name, source_topic, source_partition, source_offset)`.
- Producers must keep per-entity stable keys (`venue:canonical_symbol:timeframe` or `order_id`) to preserve partition ordering for deterministic replay.
- Invalid payloads must be rejected (fail closed) and must not mutate state.

## Schema Artifacts

Canonical JSON schemas for this ticket are under:

- `docs/design/ingestion/07-devdocs/03-lld-data-model/contracts/second-chain/*.schema.json`

## Replay Determinism Verification Contract

Representative deterministic checks are mandatory:

- Structure transition replay yields identical state/flags for identical bar sequences.
- Risk policy evaluation yields identical decision outputs for identical inputs/state/policy.
- Contract guard suite (`tests/dev-0036/run.sh`) validates topic registry + schema presence + determinism test execution.
