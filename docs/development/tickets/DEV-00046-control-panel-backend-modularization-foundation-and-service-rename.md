# DEV-00046: Control Panel Backend Modularization Foundation and Service Rename

## Status

Done (2026-04-29)

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

## Delivery Notes

- Added backend modular foundation under `services/control-panel/app/`:
  - `main.py` FastAPI bootstrap with compatibility bridge mount.
  - `api/routers/health.py` foundational health/config router.
- Added `services/control-panel/Dockerfile` and `requirements.txt`.
- Updated compose service boundary from `charting` to `control-panel` using new Dockerfile path.
- Preserved legacy startup compatibility by loading legacy charting app as mounted bridge.
- Added verification pack `tests/dev-0046/run.sh` and `make test-dev-0046`.
