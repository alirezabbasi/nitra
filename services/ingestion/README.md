# Shared Ingestion Module

This folder is a shared Python module used by multiple ingestion runtime services.

## Why it exists

`services/ingestion/` is not a duplicate of `services/market-ingestion/`.

- `services/market-ingestion/`: connector runtime that publishes raw market events.
- `services/ingestion/`: shared library code (`contracts.py`, `domain.py`) imported by:
  - `market-ingestion`
  - `market-normalization`
  - `bar-aggregation`
  - `gap-detection`
  - `backfill-worker`

## Notes

- Normalization symbol mapping source of truth is `infra/symbols/registry.v1.json`.
- Runtime venue/market activation source of truth is DB table `venue_market`.
- Runtime-generated nested `services/*/ingestion/` folders are not project source and are ignored.
