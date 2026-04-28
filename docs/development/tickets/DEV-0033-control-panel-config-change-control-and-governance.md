# DEV-0033: Control Panel Config Registry, Change Control, and Governance

## Status

Open

## Summary

Deliver centralized configuration management with validation, staged rollout, and governance controls.

## Scope

- Typed config registry browser/editor.
- Environment-aware config comparison (`dev`/`paper`/`prod`).
- Change proposal and approval workflow.
- Rollback controls with impact preview and blast-radius warnings.
- Immutable config change history.

## Non-Goals

- Arbitrary secret-value plaintext editing.
- Bypass of existing policy gates.

## Acceptance Criteria

- Config changes are validated before apply.
- Approval flow exists for high-risk changes.
- Rollback and history are first-class operator actions.

## Verification

- Config mutation and rollback integration tests.
- Approval/audit trail validation.
