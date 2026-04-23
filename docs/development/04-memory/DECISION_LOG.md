# Decision Log

## DEC-0001

- Date: 2026-04-22
- Decision: Start with ingestion baseline before broader platform modules.
- Context: Need reliable event/data spine before risk/execution/model layers.
- Impact: `DEV-00001..DEV-00007` delivered ingestion-first foundation.

## DEC-0002

- Date: 2026-04-23
- Decision: Establish development operating system and persistent memory artifacts under `docs/development/`.
- Context: Multi-session collaboration risks context drift without explicit project memory.
- Alternatives considered:
  - rely on ticket files only (rejected: insufficient cross-session state)
  - rely on chat history only (rejected: not durable in repository)
- Impact:
  - deterministic resume flow for future sessions
  - clearer governance and full-project planning structure
