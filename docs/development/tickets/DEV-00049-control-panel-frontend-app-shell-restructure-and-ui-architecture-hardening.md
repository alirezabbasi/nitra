# DEV-00049: Control Panel Frontend App-Shell Restructure and UI Architecture Hardening

## Status

Proposed (2026-04-29)

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
