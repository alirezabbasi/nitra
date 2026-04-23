# Service Interaction Contracts (LLD)

## Contract Rules

- Every message on stream is wrapped in envelope contract from `crates/contracts`.
- Idempotency is enforced via processed message ledgers where implemented.
- Topics must be declared in `infra/redpanda/topics.csv` and contracts crate.

## Change Protocol

When changing a service contract:

1. Update contract type in `crates/contracts` and/or `crates/domain`.
2. Update producer and consumer services.
3. Update topic bootstrap definitions if needed.
4. Add or update tests in relevant `tests/epic-*`.
5. Update docs in `docs/02-data-platform/` and this folder.
