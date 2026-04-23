# EPIC-10: Observability and SLO Enforcement

## Scope
- Instrument services with metrics, logs, and traces.
- Build dashboards and alert policies tied to SLOs.

## Deliverables
- Prometheus metrics and service readiness endpoints.
- Loki log labels and Tempo traces.
- Grafana dashboards and alert rules.

## Acceptance
- Incident drill shows detection->diagnosis->recovery within target RTO.

## Commit Slices
1. `feat(obs): add metrics/logging/tracing instrumentation`
2. `feat(obs): add grafana dashboards and alert policies`
