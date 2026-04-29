# DEV-00046: Control Panel Backend Modularization Foundation and Service Rename

## Status

Proposed (2026-04-29)

## Summary

Create backend modular skeleton and rename service boundary from charting-first to control-panel-first.

## Scope

- Introduce backend structure (example):
  - `services/control-panel/app/main.py`
  - `services/control-panel/app/api/routers/`
  - `services/control-panel/app/core/` (config, security, logging)
  - `services/control-panel/app/db/` (session, queries, repositories)
  - `services/control-panel/app/services/` (domain orchestration)
  - `services/control-panel/app/integrations/` (venue adapters)
- Move FastAPI bootstrap into `main.py` with router composition.
- Update container/runtime naming and compose references (`charting -> control-panel` alias strategy).
- Keep temporary legacy route compatibility where required.

## Non-Goals

- Full business logic split across all domains (handled in subsequent tickets).

## Acceptance Criteria

- Service starts from new entrypoint and serves health/config routes.
- Compose/runtime contracts updated and documented.
- Legacy startup path remains available only if required for staged migration.

## Verification

- Service boot smoke test.
- Compose integration test for renamed service wiring.
