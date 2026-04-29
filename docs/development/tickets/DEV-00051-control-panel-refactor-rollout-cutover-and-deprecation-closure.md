# DEV-00051: Control Panel Refactor Rollout, Cutover, and Deprecation Closure

## Status

Done (2026-04-29)

## Summary

Execute phased rollout from monolith to modular service, including compatibility period, operational monitoring, and removal of legacy paths.

## Scope

- Define phased cutover (shadow validation -> primary switch -> cleanup).
- Add observability for endpoint errors, UI load failures, and latency regressions.
- Document rollback triggers and rollback command runbooks.
- Remove temporary compatibility shims after acceptance window.

## Acceptance Criteria

- Cutover completed with no Sev-1 regression on control-panel/charting critical workflows.
- Legacy monolithic files are removed or archived with explicit closure note.
- Operations runbook and deprecation report published.

## Verification

- Production-like smoke/UAT checklist signed.
- Rollback drill evidence captured.

## Delivery Notes

- Retired temporary legacy charting alias routes from control-panel charting router.
- Established native cutover status signaling:
  - `services/control-panel/app/api/routers/health.py`
  - `/api/v1/config` now reports `native-charting-cutover` and retired alias state.
  - `/api/v1/control-panel/migration/status` added for migration phase visibility.
- Added `X-Nitra-Compat` response headers for native/legacy proxy modes in charting bridge service.
- Added rollout and rollback operational runbook:
  - `docs/design/ingestion/06-devops/control-panel-rollout-cutover-runbook.md`
- Added deprecation closure report:
  - `docs/design/ingestion/06-devops/control-panel-deprecation-closure-report.md`
- Added verification pack:
  - `tests/dev-0051/run.sh`
  - `make test-dev-0051`
