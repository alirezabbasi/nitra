# DEV-00030: Control Panel Charting Workbench Integration

## Status

Done (2026-04-29)

## Summary

Integrate charting as a first-class sub-module in the control panel, including instrument profiles with direct full-chart transitions.

## Scope

- Instrument profile view with market metadata and operational context.
- `Full Chart` action to open chart workspace for selected instrument.
- Context handoff from ops tables (risk/execution/portfolio) into chart module.
- Split-view mode: data/ops panel + chart panel.
- Snapshot/export hooks aligned with operator workflows.

## Non-Goals

- Rewrite of existing chart rendering engine.
- Mobile-first charting redesign.

## Acceptance Criteria

- Instrument-driven chart navigation is seamless and deep-linkable.
- Operators can pivot from events/orders/risk state to chart context in one click.
- Chart module remains continuous with live feed behavior.

## Verification

- Navigation integration tests for instrument -> chart transitions.
- UX regression checks for chart continuity and context carryover.
- `tests/dev-00030/run.sh`
