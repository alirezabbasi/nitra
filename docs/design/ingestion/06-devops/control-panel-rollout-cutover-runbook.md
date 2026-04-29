# Control Panel Rollout, Cutover, and Rollback Runbook

## Scope

Operational runbook for `DEV-00051` cutover from compatibility-shim mode to native control-panel charting routes.

## Phases

1. Shadow validation
- Run `scripts/ci/control_panel_refactor_quality_gate.sh` on target branch.
- Validate critical workflows with `tests/dev-0051/run.sh`.
- Capture baseline latency/error snapshots for control-panel endpoints.

2. Primary switch
- Confirm `/api/v1/config` reports `compat_mode=native-charting-cutover`.
- Keep charting under `/api/v1/charting/*` as canonical endpoint family.
- Retire legacy compatibility aliases (`/api/v1/bars/*`, `/api/v1/ticks/*`, `/api/v1/markets/*`, `/api/v1/venues/*`, `/api/v1/backfill/*`, `/api/v1/coverage/*`).

3. Cleanup
- Publish deprecation closure report.
- Update LLD + migration map status artifacts.
- Maintain only native endpoint observability paths.

## Monitoring Watchlist

- Endpoint-level error rate for:
  - `/control-panel`
  - `/api/v1/control-panel/*`
  - `/api/v1/charting/*`
- UI load failures (`/control-panel-assets/*` fetch errors).
- Latency regressions versus pre-cutover baseline.

## Rollback Triggers

- Sev-1 regression on control-panel critical workflow.
- Sustained 5xx rate above operational threshold.
- Charting handoff failure (`openChartWorkbench`/full-chart link break) across core symbols.

## Rollback Procedure

1. Halt rollout and capture evidence (failing route list, timestamps, logs).
2. Revert deployment to previous known-good image/commit.
3. Re-run:
- `scripts/ci/control_panel_refactor_quality_gate.sh`
- `make session-bootstrap`
4. Record rollback evidence in debugging log and session ledger.

## Validation Commands

- `make test-dev-0051`
- `make enforce-section-5-1`
- `make session-bootstrap`
