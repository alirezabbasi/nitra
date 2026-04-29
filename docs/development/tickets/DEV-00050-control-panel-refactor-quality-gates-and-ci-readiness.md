# DEV-00050: Control Panel Refactor Quality Gates and CI Readiness

## Status

Proposed (2026-04-29)

## Summary

Add test harnesses and CI gates tailored to the refactored backend/frontend architecture.

## Scope

- Add backend unit/integration tests per router/service/repository layer.
- Add frontend tests for route rendering, API client behavior, and critical interactions.
- Add contract tests for compatibility endpoints.
- Add lint/typecheck/format gates for backend and frontend paths.
- Ensure deterministic, containerized CI commands and docs.

## Acceptance Criteria

- Refactor branches cannot merge without passing required backend/frontend/contract checks.
- Test evidence for parity-critical workflows is available.

## Verification

- `tests/dev-00050/run.sh` plus documented command outputs.
