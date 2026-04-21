# Symbol Registry (EPIC-04)

## Current Registry Artifact

- File: `infra/symbols/registry.v1.json`
- Mounted into normalizer container as read-only.

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

## Change Process

1. Add/edit mappings in registry JSON.
2. Validate with EPIC-04 tests.
3. Deploy normalizer with updated registry file.
4. Record mapping changes in release notes and docs.
