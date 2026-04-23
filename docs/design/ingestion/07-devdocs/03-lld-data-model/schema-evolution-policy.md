# Schema Evolution Policy (LLD)

## Rules

- No breaking schema change without migration notes and backward compatibility plan.
- Additive changes are preferred over destructive modifications.
- New entities must include:
  - primary key strategy,
  - event time and ingestion time,
  - idempotency key,
  - retention/archive policy,
  - validation tests.

## Minimum Change Set for New Entity

1. Migration SQL under `infra/timescaledb/init/` (or versioned migration path when introduced).
2. Domain/contract type updates.
3. Service read/write integration.
4. Test coverage in corresponding `tests/dev-*` or module-specific test packs.
5. Docs updates in `docs/design/ingestion/02-data-platform/` and `docs/design/ingestion/07-devdocs/03-lld-data-model/`.
