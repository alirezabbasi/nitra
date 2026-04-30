# DEV-00151: Control Panel Foundation - unified configuration registry core

## Status

Planned

## Goal

Deliver the core configuration registry primitives for control-panel managed configuration:
- typed config schema,
- validation engine,
- RBAC policy gates,
- approval/rollback transaction model.

## Scope

- Core config entity model and schema/version contracts.
- Validation pipeline (schema + semantic + environment policy checks).
- RBAC and approval workflow primitives.
- Rollback contract and immutable change-history persistence.

## Non-Goals

- Module-by-module migration/adoption of existing config surfaces (`DEV-00152`).

## Acceptance Criteria

- Registry supports typed entries with explicit schema/version metadata.
- Invalid config changes are blocked deterministically before apply.
- Privileged config changes require approval + audit evidence.
- Rollback path is deterministic and fully auditable.

## Verification

- Run the relevant `make test-*` target(s) for this scope.
- `make enforce-section-5-1`
- `make session-bootstrap`
