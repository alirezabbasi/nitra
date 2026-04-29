# Control Panel Deprecation Closure Report

## Closure date

- 2026-04-29

## Acceptance window

- Compatibility alias acceptance window ended with `DEV-00051` closure.

## Retired routes

- `/api/v1/bars/*`
- `/api/v1/ticks/*`
- `/api/v1/markets/*`
- `/api/v1/venues/*`
- `/api/v1/backfill/*`
- `/api/v1/coverage/*`

Canonical replacement family:
- `/api/v1/charting/*`

## Operational verification

- `make test-dev-0051` pass.
- `make enforce-section-5-1` pass.
- `make session-bootstrap` pass.

## Rollback drill evidence

- Rollback procedure validated via runbook command path and gate sequence.
- Recovery path maintained through previous deploy artifact restoration workflow.

## Closure note

Legacy compatibility shims for charting aliases are retired. Control-panel charting cutover is now native-first with migration status exposed at `/api/v1/control-panel/migration/status`.
