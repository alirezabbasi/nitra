# Operations, Backup, and Disaster Recovery

## SRE/Operations Baseline

- Service health and readiness probes required.
- Metrics/logs/traces exported to Grafana stack.
- Alerts must map to actionable runbooks.

## Backup Plan

- TimescaleDB scheduled backups and restore drill cadence.
- ClickHouse backup policy for analytical data durability.
- MinIO bucket replication/versioning strategy.
- Configuration backup for Compose and environment manifests.

## DR Plan

- Define RPO/RTO targets by environment.
- Warm restore plan for same-region recovery.
- Cold restore plan for catastrophic failure.
- Quarterly recovery drills with evidence logs.

## Operational Readiness Criteria

- Rollback procedure tested.
- On-call runbooks validated.
- SLO dashboard coverage in place.
- Data integrity checks automated for hot/cold/archive flows.
