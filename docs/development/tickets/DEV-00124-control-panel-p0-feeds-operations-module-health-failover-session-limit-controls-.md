# DEV-00124: Control Panel (P0) - feeds operations module (health/failover/session/limit controls + guarded config).

## Status

Done (2026-05-01)

## Goal

Define and deliver: Control Panel (P0) - feeds operations module (health/failover/session/limit controls + guarded config).

## Scope

- Implementation changes required by this ticket.
- Test coverage and verification evidence for this ticket.
- Documentation and operational updates needed for closeout.

## Acceptance Criteria

- Behavior/contract described in the goal is implemented.
- Deterministic and regression tests are added/updated.
- Relevant docs/runbooks are updated.
- Kanban and memory artifacts are synchronized with final status.

## Verification

- `make test-dev-0068`
- `make enforce-section-5-1`
- `make session-bootstrap`

## Delivered Artifacts

- `services/control-panel/app/api/routers/ingestion.py`
  - failover policy proxy route
- `services/control-panel/frontend/src/control-panel.html`
  - ingestion failover policy controls section
- `services/control-panel/frontend/src/app/control-panel.js`
  - failover policy runtime rendering and guarded submission flow
- `services/control-panel/frontend/dist/*`
  - synced runtime assets via `scripts/frontend/build_control_panel_frontend.sh`
