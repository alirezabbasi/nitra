# DEV-00049: Control Panel Frontend App-Shell Restructure and UI Architecture Hardening

## Status

Done (2026-04-29)

## Summary

Replace single-file control-panel HTML architecture with a scalable frontend module structure suitable for long-term team development.

## Scope

- Introduce frontend structure under service boundary (example):
  - `frontend/src/app/` (shell, routing, layout)
  - `frontend/src/modules/` (overview/ingestion/risk/execution/charting/ops/research/config)
  - `frontend/src/components/` (shared UI primitives)
  - `frontend/src/services/` (API client, auth/session, error handling)
  - `frontend/src/state/` (session/preferences/query state)
  - `frontend/src/styles/` (design tokens/theme)
- Break inline JS/CSS into typed modules and reusable components.
- Keep role-aware navigation and command palette behavior.
- Maintain chart embed/full-chart transitions.

## Non-Goals

- Visual redesign beyond architecture and production-grade consistency polish.

## Acceptance Criteria

- No monolithic single-file UI runtime for control panel.
- Route/module ownership is clear and independently maintainable.
- Build and asset pipeline is documented and reproducible in Docker.

## Verification

- Frontend route smoke tests.
- Accessibility and keyboard interaction regression checks.
- UI parity checklist for core modules.

## Delivery Notes

- Added frontend source structure under control-panel boundary:
  - `services/control-panel/frontend/src/app/`
  - `services/control-panel/frontend/src/modules/`
  - `services/control-panel/frontend/src/components/`
  - `services/control-panel/frontend/src/services/`
  - `services/control-panel/frontend/src/state/`
  - `services/control-panel/frontend/src/styles/`
- Split monolithic inline runtime:
  - extracted stylesheet to `src/styles/control-panel.css`
  - extracted app shell runtime to `src/app/control-panel.js`
  - extracted shared API/state/format helpers to modular files
- Added reproducible frontend build/sync pipeline:
  - `scripts/frontend/build_control_panel_frontend.sh` (`src -> dist`)
  - `services/control-panel/frontend/dist/` as runtime artifact
- Updated control-panel service to serve frontend directly:
  - `/control-panel` now served by `services/control-panel/app/main.py`
  - assets mounted at `/control-panel-assets`
  - Dockerfile copies `frontend/dist` into runtime image
- Added verification pack `tests/dev-0049/run.sh` and `make test-dev-0049`.
