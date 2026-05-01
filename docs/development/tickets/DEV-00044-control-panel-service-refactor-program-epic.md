# DEV-00044: Control Panel Service Refactor Program Epic

## Status

In Progress (2026-04-29)

## Summary

Refactor the current `services/charting` monolith into a production-grade `control-panel-service` with modular FastAPI backend architecture and a scalable frontend application structure. Charting remains first-class but is integrated as a module inside the control panel service boundary.

## Problem Statement

Current implementation quality is functionally rich but structurally fragile:

- Backend concern sprawl: `services/charting/app.py` mixes routing, auth, RBAC, SQL access, business logic, external adapters, and view serving in a single file.
- Frontend concern sprawl: `services/charting/static/control-panel.html` combines markup, styling, navigation, rendering logic, and network operations in one document.
- Limited operability at team scale: high merge conflict probability, weak test isolation, and difficult ownership boundaries for domain teams.

## Goals

- Rename and reposition the service as `control-panel-service` (charting becomes a module).
- Introduce purpose-driven backend modules with explicit boundaries.
- Introduce standard frontend app architecture (shell, routes/modules, shared UI primitives, services/state).
- Preserve existing API/UI behavior through compatibility windows and regression tests.
- Keep Docker-first runtime and documentation contracts synchronized.

## Non-Goals

- No rewrite of deterministic Rust core services.
- No product-scope expansion beyond structural refactor and production readiness hardening.
- No breaking API changes without explicit migration and compatibility contract.

## Decomposed Tickets

1. `DEV-00045` target architecture and migration contract freeze.
2. `DEV-00046` backend modularization foundation and service rename.
3. `DEV-00047` control-panel domain router split and service-layer extraction.
4. `DEV-00048` charting module extraction and compatibility bridge.
5. `DEV-00049` frontend app-shell restructure and UI architecture hardening.
6. `DEV-00050` quality gates, contract tests, and CI readiness for refactor.
7. `DEV-00051` rollout, cutover, observability, and deprecation closure.

## Acceptance Criteria

- New service structure is implemented and documented with clear module ownership.
- Backend and frontend both follow production-grade separation of concerns.
- Existing high-value workflows (overview/ingestion/risk/execution/charting/ops/research/config) remain functional.
- Tests and CI evidence cover compatibility, regressions, and operability.
- Legacy monolithic files are either removed or retained only as temporary compatibility shims with explicit retirement date.

## Definition of Done

A ticket is complete only when all conditions below are true:

- Acceptance Criteria are fully met without unresolved scope gaps.
- Required implementation is merged in this repository and aligned with HLD/LLD constraints.
- Tests are added/updated for the scope and passing evidence is recorded.
- Operational/documentation artifacts for the scope are updated (runbooks/contracts/docs as applicable).
- Execution tracking and memory artifacts are synchronized (`KANBAN`, `CURRENT_STATE`, `SESSION_LEDGER`).
- Residual risks, assumptions, and follow-up actions are explicitly documented.

## Verification

- Ticket-level verification evidence across `tests/dev-00045` .. `tests/dev-00051`.
- Compose runtime smoke validation and endpoint/UI parity checks.
- Architecture docs updated under `docs/design/ingestion/07-devdocs/04-lld-services/`.

## Delivery Notes

- Program decomposition tickets `DEV-00045..DEV-00051` are published and linked.
- Target service LLD baseline exists at `docs/design/ingestion/07-devdocs/04-lld-services/control-panel-service.md`.
- Program baseline verification pack added at `tests/dev-0044/run.sh` with `make test-dev-0044`.
- `DEV-00045` completed: architecture freeze, migration map, and compatibility matrix contracts published.
- `DEV-00046` completed: backend modular foundation created with compose service-boundary rename (`charting` -> `control-panel`) and legacy bridge startup path.
- `DEV-00047` completed: control-panel domain routers extracted with service-layer proxy bridge and compatibility fallback retained.
