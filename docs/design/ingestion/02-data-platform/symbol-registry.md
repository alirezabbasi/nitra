# Symbol Registry (EPIC-04)

## Current Registry Artifact

- File: `infra/symbols/registry.v1.json`
- Mounted into normalizer container as read-only.
- DB runtime table: `venue_market` (init migration `infra/timescaledb/init/005_venue_market.sql`)

## Registry Schema

- `version`
- `mappings[]`
  - `venue`
  - `broker_symbol`
  - `canonical_symbol`
  - `asset_class`

## Design Notes

- Keys are normalized by `venue` (lowercase) and `broker_symbol` (uppercase).
- Registry version is logged at normalizer startup.
- Missing mappings are fail-closed by default.
- Runtime ingestion activation and chart venue/market settings are DB-driven through `venue_market`.
- File registry remains authoritative for normalization mapping contracts.

## Change Process

1. Add/edit mappings in registry JSON.
2. Validate with EPIC-04 tests.
3. Deploy normalizer with updated registry file.
4. Record mapping changes in release notes and docs.
