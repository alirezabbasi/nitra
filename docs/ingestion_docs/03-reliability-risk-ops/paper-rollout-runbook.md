# Paper Rollout Runbook

## Purpose

Define the required daily operating procedure for paper mode before any micro-live promotion.

## Entry Criteria

1. `docker compose up -d` succeeds from repository root.
2. `make health` shows all critical services running.
3. EPIC step tests are green (`./tests/run-all.sh`).
4. Risk controls enabled (`RISK_KILL_SWITCH=false` only for planned sessions).

## Daily Session Procedure

1. Pre-open checks (T-30m):
- Verify data stream health in Grafana.
- Verify risk and OMS readiness endpoints.
- Verify no unresolved critical alerts.

2. Open-session controls:
- Monitor `risk_gateway_orders_rejected_total` and `oms_reconcile_hold_total`.
- Track gap and replay events for anomalies.
- Document any intervention in the session log.

3. Post-session closure:
- Run reconciliation query pack and confirm no unexplained mismatch growth.
- Complete `templates/daily-reconciliation-report.md`.
- Record sign-off from engineering on duty.

## Multi-Week Stability Requirement

- Minimum paper evidence window: 15 consecutive trading days.
- Zero unexplained data-loss incidents.
- All critical alerts diagnosed and closed with notes.

## Escalation

If any critical issue appears:
1. Enable kill switch if execution safety is uncertain.
2. Freeze promotion activity.
3. Open incident and attach logs/metrics evidence.
