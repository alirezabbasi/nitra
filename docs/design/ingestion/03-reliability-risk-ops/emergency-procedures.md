# Emergency Procedures

## Priority Order

1. Protect capital and execution safety.
2. Preserve data and forensic evidence.
3. Restore stable paper operations.

## Emergency Actions

1. Activate kill switch (`RISK_KILL_SWITCH=true`).
2. Pause any micro-live execution activity.
3. Confirm data pipelines remain online for observability.
4. Announce incident channel update with timestamp and owner.

## Incident Evidence Pack

Capture and attach:

- Grafana dashboard snapshots (`BarsFP Overview`, `BarsFP SLO Signals`).
- Relevant logs from `risk-gateway`, `oms`, and stream services.
- Current reconciliation report template for the affected date.

## Recovery Handoff

- Engineering owner:
- Risk owner:
- Ops owner:
- Next decision checkpoint time (UTC):

## Closure

An incident is considered closed only after:

1. Root-cause and corrective actions documented.
2. Closure gate re-run with `PASS`.
3. All three owners sign off.
