# Bug Registry

This directory is the canonical bug registry for NITRA ingestion.

- Every discovered bug must be documented here with a unique code.
- Naming convention: `BUG-00001.md`, `BUG-00002.md`, ...
- Each bug file must include:
  - description and impact,
  - reproducible trigger/steps,
  - root cause analysis,
  - resolution details,
  - verification evidence and status.

Current entries:
- `BUG-00001`: TimescaleDB bootstrap halts before creating `raw_tick` and related tables.
- `BUG-00002`: `market-normalization` crash loop on duplicate processed-message ledger offsets.
- `BUG-00003`: mock ingestion projected identical FX-like prices across all instruments (including crypto).
