# EPIC-09: Risk Gateway and OMS

## Scope
- Build non-bypassable pre-trade risk checks.
- Implement order state machine and reconciliation.

## Deliverables
- Risk gateway service.
- OMS with idempotent submission and fill handling.
- Reconciliation loop and mismatch policies.

## Acceptance
- Every order path is blocked on risk decision.

## Commit Slices
1. `feat(risk): add pre-trade and post-trade controls`
2. `feat(oms): add order lifecycle and reconciliation`
