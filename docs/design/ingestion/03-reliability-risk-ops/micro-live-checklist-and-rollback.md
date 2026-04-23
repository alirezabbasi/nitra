# Micro-Live Checklist and Rollback Protocol

## Objective

Promote from `paper` to limited-capital micro-live mode only when all gates pass.

## Limited-Capital Guardrails

1. Keep `RISK_MAX_ORDER_QTY` and `RISK_MAX_ORDER_NOTIONAL` at micro-live limits.
2. Set `RISK_MAX_DAILY_FILLED_NOTIONAL` to strict daily cap.
3. Keep kill-switch control operational and tested before session start.
4. Allow only approved symbols and strategy IDs.

## Promotion Checklist (Go/No-Go)

1. Paper evidence window complete (15 sessions minimum).
2. No open critical incidents.
3. Latest closure gate output is `PASS`.
4. Product, risk, and ops approvals captured.
5. Rollback owner assigned for the session.

## Rollback Triggers

Immediate rollback to paper-only mode if any occurs:

1. Risk gateway unavailable for more than 2 minutes.
2. OMS reconciliation-hold growth exceeds threshold.
3. Unexpected reject-rate spike without understood cause.
4. Data quality degradation impacting execution trust.

## Rollback Procedure

1. Enable kill switch immediately (`RISK_KILL_SWITCH=true`).
2. Stop promotion path and mark environment status as `HOLD`.
3. Preserve all logs, metrics snapshots, and reconciliation evidence.
4. Run incident protocol and root-cause triage.
5. Revert to paper controls and complete post-incident report.

## Post-Rollback Exit Criteria

- Root cause identified and mitigated.
- Closure gate re-run and passing.
- Re-approval by engineering, risk, and ops.
