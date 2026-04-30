# DEV-00063: Control-Panel Post-Cutover Observability Revalidation

## Status

Done (2026-04-30)

## Goal

Re-validate control-panel post-cutover observability thresholds under sustained runtime load using a repeatable evidence-capture workflow.

## Scope

- Define explicit sustained-load thresholds for control-panel cutover health checks.
- Add executable probe script for repeated endpoint sampling under load.
- Add `dev-0063` verification pack to keep the runbook/script contract enforced.
- Capture and store runtime evidence report under `docs/development/debugging/reports/`.

## Endpoints

- `/control-panel`
- `/api/v1/config`
- `/api/v1/control-panel/migration/status`
- `/api/v1/control-panel/overview`
- `/api/v1/charting/markets/available`

## Acceptance Criteria

- A deterministic probe command exists and can generate a timestamped report.
- Runbook contains explicit threshold values and pass/fail criteria.
- `tests/dev-0063/run.sh` validates script + runbook + ticket wiring.
- Kanban/current-state/memory reflect `DEV-00063` tracking state.

## Verification

- `make test-dev-0063`
- `make enforce-section-5-1`
- Optional live run:
  - `scripts/observability/control_panel_cutover_sustained_check.sh`

## Evidence

- `docs/development/debugging/reports/control-panel-observability-revalidation-2026-04-30.md`
