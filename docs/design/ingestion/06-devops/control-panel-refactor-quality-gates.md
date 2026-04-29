# Control Panel Refactor Quality Gates

## Purpose

Defines deterministic, repository-local quality gates for control-panel refactor slices (`DEV-00050`).

## Required Gate Command

- Primary CI-ready command:
  - `scripts/ci/control_panel_refactor_quality_gate.sh`
- Equivalent explicit sequence:
  1. `make test-dev-0050`
  2. `make enforce-section-5-1`
  3. `make session-bootstrap`

## Coverage

`tests/dev-0050/run.sh` enforces:

- Compatibility contract checks
  - `tests/dev-0048/run.sh`
  - `tests/dev-0049/run.sh`
- Backend quality baseline
  - Python compile checks for `services/control-panel/app/*`
  - Router-layer SQL hygiene guard (no inline SQL in router handlers)
- Frontend quality baseline
  - reproducible frontend build (`scripts/frontend/build_control_panel_frontend.sh`)
  - source/dist parity checks for:
    - `control-panel.html`
    - `styles/control-panel.css`
    - `app/control-panel.js`
- Route/contract smoke checks
  - `tests/dev-0050/smoke_control_panel_routes.py`
  - validates control-panel native, charting-native, and legacy compatibility endpoint presence.

## Determinism Expectations

- Gate commands must be runnable from repository root.
- No host-global runtime assumptions beyond project dependencies.
- Failing any step must return non-zero and block merge/promotion.
