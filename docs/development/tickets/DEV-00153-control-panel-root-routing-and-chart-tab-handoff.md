# DEV-00153: Control-panel root routing and chart-tab handoff

## Status

Done (2026-05-01)

## Goal

Make port `8110` root (`/`) open the control panel by default, and move charting view access to a dedicated tab-launch flow that opens in a new browser tab with instrument-aware context.

## Scope

- Route swap so control-panel UI is served at `/`.
- Add charting page route and deep-link behavior for charting context.
- Replace in-panel chart row actions with new-tab chart actions.
- Add default-first-instrument fallback when chart launch occurs from general context.

## Acceptance Criteria

- Visiting `/` on control-panel service opens the control panel.
- Charting view can be opened in a new browser tab.
- Row-level chart actions open charts for that specific `venue:symbol`.
- General chart launch opens first available instrument when no specific instrument is provided.
- Frontend `src -> dist` assets are synced and runtime-compatible.

## Verification

- `scripts/frontend/build_control_panel_frontend.sh`
- `PYTHONPYCACHEPREFIX=/tmp/pycache python -m py_compile services/control-panel/app/main.py services/charting/app.py`
- `make session-bootstrap`

## Delivered Artifacts

- `services/control-panel/app/main.py`
  - root route now serves control panel
  - added `/charting` route for charting view page
- `services/charting/app.py`
  - charting profile deep link updated to `/charting?...`
- `services/control-panel/frontend/src/app/control-panel.js`
  - added `openChartTab` behavior with instrument-aware fallback
  - row chart actions now launch new tab
- `services/control-panel/frontend/src/control-panel.html`
  - added chart workbench button to open chart in a new tab
- `services/control-panel/frontend/dist/*`
  - synced from `src` via frontend build script
