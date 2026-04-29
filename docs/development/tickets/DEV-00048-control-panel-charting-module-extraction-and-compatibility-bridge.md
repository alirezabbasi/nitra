# DEV-00048: Control Panel Charting Module Extraction and Compatibility Bridge

## Status

Proposed (2026-04-29)

## Summary

Extract charting-specific APIs and adapter logic into a dedicated charting module within control-panel service, preserving existing chart workflows.

## Scope

- Move charting routes to dedicated router module (`bars`, `ticks`, `markets`, `venues`, `backfill`, `coverage`, `charting profile`).
- Isolate venue adapter clients and retry policy logic from control-panel domain code.
- Preserve existing chart URLs and control-panel chart handoff compatibility.
- Add compatibility shims and deprecation headers where endpoint paths evolve.

## Acceptance Criteria

- Charting module is independently testable within service boundary.
- Control-panel and charting modules share common infrastructure without circular coupling.
- Existing chart UI and instrument handoff continue working.

## Verification

- Chart endpoint parity tests (`bars`, `history`, `ticks`, backfill/coverage).
- Integration test: control-panel -> charting workbench handoff.
