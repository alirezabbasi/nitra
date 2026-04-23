# Daily Reconciliation Report Template

- Date (UTC):
- Environment: `paper`
- Session owner:

## Health Snapshot

- Stream ingestion: `OK / DEGRADED / FAIL`
- Risk gateway: `OK / DEGRADED / FAIL`
- OMS: `OK / DEGRADED / FAIL`
- Gap backlog: `OK / DEGRADED / FAIL`

## Quantitative Checks

- `risk_gateway_orders_processed_total` delta:
- `risk_gateway_orders_rejected_total` delta:
- `oms_orders_submitted_total` delta:
- `oms_reconcile_hold_total` delta:
- Open unresolved gaps (count):

## Reconciliation Findings

- Unexpected mismatches:
- Actions taken:
- Replay/backfill operations executed:

## Incidents

- Incident IDs (if any):
- Severity:
- Resolution status:

## Decision

- Paper session outcome: `PASS / CONDITIONAL / FAIL`
- Promotion impact: `NONE / HOLD MICRO-LIVE / ROLLBACK`

## Sign-Off

- Engineering:
- Risk:
- Ops:
