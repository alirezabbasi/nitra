# DEV-00069: Exchange/Broker Feeds - credential/session lifecycle hardening (token refresh, expiration guardrails, auth error classification).

## Status

Done (2026-05-01)

## Goal

Define and deliver: Exchange/Broker Feeds - credential/session lifecycle hardening (token refresh, expiration guardrails, auth error classification).

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
  - `control_panel_ingestion_session_policy` table contract and seed path.
  - `POST /api/v1/control-panel/ingestion/session-policy` guarded mutation endpoint.
  - `GET /api/v1/control-panel/ingestion` payload includes `session_policies` + `session_runtime`.
- `services/control-panel/frontend/src/control-panel.html`
  - session lifecycle policy table + update form.
- `services/control-panel/frontend/src/app/control-panel.js`
  - session lifecycle runtime render + guarded submit handler.

## Notes

- This ticket file was generated to restore ticket-registry integrity from `KANBAN.md`.
