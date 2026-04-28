# DEV-00029: Control Panel Execution OMS and Broker Operations Center

## Status

Open

## Summary

Provide professional OMS workflows for order lifecycle monitoring, broker adapter diagnostics, and reconciliation operations.

## Scope

- Order blotter with advanced filtering and lifecycle timeline.
- Amend/cancel workflows with role-gated controls.
- Broker adapter health and error classification panels.
- Reconciliation queue and exception handling workflow.
- Terminal state diagnostics (rejected/cancelled/orphaned ack flows).

## Non-Goals

- Auto-trading strategy authoring UI.
- Broker onboarding automation.

## Acceptance Criteria

- Operators can inspect and manage full order lifecycle.
- Adapter failures and reconciliation exceptions are triageable.
- All mutating actions are auditable and permission-gated.

## Verification

- OMS workflow integration tests.
- End-to-end validation with simulated broker ack/fill paths.
