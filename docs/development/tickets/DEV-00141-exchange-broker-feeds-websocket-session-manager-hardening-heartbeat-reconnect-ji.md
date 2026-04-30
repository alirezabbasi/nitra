# DEV-00141: Exchange/Broker Feeds - websocket/session manager hardening (heartbeat, reconnect jitter/backoff, stale-session detection).

## Status

Done (2026-05-01)

## Goal

Define and deliver: Exchange/Broker Feeds - websocket/session manager hardening (heartbeat, reconnect jitter/backoff, stale-session detection).

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

- `make test-dev-0069`
- `make enforce-section-5-1`
- `make session-bootstrap`

## Delivered Artifacts

- `services/charting/app.py`
  - `control_panel_ingestion_ws_policy` table contract and seed path.
  - `POST /api/v1/control-panel/ingestion/ws-policy` guarded mutation endpoint.
  - `GET /api/v1/control-panel/ingestion` payload includes `ws_policies` + `ws_runtime`.
- `services/control-panel/frontend/src/control-panel.html`
  - websocket/session runtime policy table + update form.
- `services/control-panel/frontend/src/app/control-panel.js`
  - websocket/session runtime render + guarded submit handler.

## Notes

- This ticket file was generated to restore ticket-registry integrity from `KANBAN.md`.
