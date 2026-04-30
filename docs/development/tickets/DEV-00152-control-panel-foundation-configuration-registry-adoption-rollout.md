# DEV-00152: Control Panel Foundation - configuration registry adoption rollout

## Status

Planned

## Goal

Adopt the unified configuration registry across all control-panel modules and migrate legacy configuration paths without behavior regression.

## Scope

- Module-by-module configuration inventory and migration sequencing.
- Compatibility bridge for legacy config paths during cutover.
- Regression checks that each module uses registry-backed configuration.
- Rollout and rollback runbook updates.

## Non-Goals

- Core registry primitive implementation (`DEV-00151`).

## Acceptance Criteria

- Every control-panel module with mutable config uses registry-backed contracts.
- Legacy config paths are either retired or explicitly bridged with deprecation policy.
- Migration includes rollback-safe steps and verified regression coverage.
- Kanban/memory artifacts reflect completion only after full module adoption.

## Verification

- Run the relevant `make test-*` target(s) for this scope.
- `make enforce-section-5-1`
- `make session-bootstrap`
