# DEV-00005: Minimal Ingestion Service Wire-Up in NITRA Compose

## Status

Open

## Summary

Wire the minimum viable ingestion services into NITRA compose and service folders to run raw event ingestion through canonical persistence.

## Scope

- Implement/adapt and wire:
  - connector
  - normalizer
  - bar engine
  - gap detector/backfill trigger (minimal scope)
- Keep compose profile intentionally simple for development.

## Hard Exclusions

- Do not import legacy/noise services not needed for live ingestion validation.
- Do not import heavy monitoring bundle from BarsFP.
- Do not introduce parallel alternate ingestion pipelines.

## Deliverables

1. Service code wired under NITRA service structure.
2. Compose updates for minimal end-to-end ingestion runtime.
3. Environment variable schema docs for new services.

## Acceptance Criteria

- A developer can bring ingestion path up with documented commands.
- Raw events flow to canonical entities.
- Compose remains concise and maintainable for dev usage.

