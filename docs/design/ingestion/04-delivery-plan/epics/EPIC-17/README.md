# EPIC-17: Observability Maturity and SLO Automation

## Scope
- Standardize metrics, tracing, and logs across all services.
- Strengthen SLO-driven alerting with actionable runbook linkage.

## Deliverables
- Unified telemetry instrumentation contract (metrics/traces/log fields).
- Correlation IDs across event flow for cross-service diagnosis.
- Burn-rate and error-budget alert policy updates.

## Acceptance
- Incident drill validates end-to-end detection, diagnosis, and recovery workflow.

## Commit Slices
1. `feat(obs): unify telemetry contract across services`
2. `feat(slo): add burn-rate alerts and runbook-linked policies`
