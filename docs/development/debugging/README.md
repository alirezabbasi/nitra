# Debugging Registry

This directory is the canonical debugging registry for NITRA.

- Every discovered bug must be documented here with a unique code.
- Naming convention: `BUG-00001.md`, `BUG-00002.md`, ...
- Each bug file must include:
  - description and impact,
  - reproducible trigger/steps,
  - root cause analysis,
  - resolution details,
  - verification evidence and status.
- Every debugging/development command must be logged in `debugcmd.md` with timestamp, command, and purpose.

Current entries:
- `BUG-00001`: TimescaleDB bootstrap halts before creating `raw_tick` and related tables.
- `BUG-00002`: `market-normalization` crash loop on duplicate processed-message ledger offsets.
- `BUG-00003`: mock ingestion projected identical FX-like prices across all instruments (including crypto).
- `BUG-00004`: manual chart backfill reported success without enforcing full 90-day `1m` continuity.
- `BUG-00005`: Coinbase "live" feed was mock-generated; resolved in code with venue-sourced ingestion and fail-closed no-mock guardrails.
- `BUG-00006`: startup 90-day backfill stalls with high `failed_no_source_data` volume due replay source-depth gap.
- `BUG-00007`: OANDA/Capital connectors degraded after no-mock cutover due URL/auth/error handling defects (resolved in code; restart required).
- `BUG-00008`: OANDA/Capital quotes ingested but no OHLCV persisted due stale exchange timestamp bucketing in bar aggregation (resolved in code; restart required).
